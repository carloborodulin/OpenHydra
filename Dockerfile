# OpenHydra: one image. FastAPI serves the API and the built dashboard.
# Stages: build the web -> build the DuckDB marts (dbt) from the seed -> runtime.
#
# Base images are pinned by digest, so a rebuild of an old commit gets the same
# images. Dependabot proposes digest updates. The uv image digest is the
# python3.12-bookworm-slim tag of 2026-11-22 (uv 0.9.30, per its annotation).
ARG NODE_IMAGE=node:26-slim@sha256:e6bedef217677b276c591795e169840edd9096dbf13f29df8ef8d1856b8820bc
ARG UV_IMAGE=ghcr.io/astral-sh/uv:python3.12-bookworm-slim@sha256:e5b65587bce7de595f299855d7385fe7fca39b8a74baa261ba1b7147afa78e58

# ---- 1. build the dashboard ------------------------------------------------
FROM ${NODE_IMAGE} AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build      # -> /app/web/dist

# ---- 2. build the DuckDB marts from the committed seed --------------------
FROM ${UV_IMAGE} AS data
WORKDIR /app/warehouse
# Install dbt from the warehouse lock first (a cached layer). The lock pins the
# DuckDB writer to the same version as the API reader.
COPY warehouse/pyproject.toml warehouse/uv.lock ./
RUN uv sync --frozen --only-group dbt --no-install-project
COPY warehouse/dbt/ ./dbt/
COPY deploy/seed/ /app/data/raw/
# Committed reference seeds read directly by dbt (the Census population CSV).
COPY data/seeds/ /app/data/seeds/
WORKDIR /app/warehouse/dbt
# dbt reads ../../data/raw/*.parquet (relative to CWD) and writes ../openhydra.duckdb
RUN ../.venv/bin/dbt build --profiles-dir .

# ---- 3. API runtime --------------------------------------------------------
FROM ${UV_IMAGE} AS final
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app/api
# Third-party dependencies first (a cached layer that changes only with the lock).
COPY api/pyproject.toml api/uv.lock ./
COPY cdeclient/pyproject.toml /app/cdeclient/pyproject.toml
RUN uv sync --frozen --no-dev --no-install-project --no-install-local
# Then the two local packages, installed into the venv (not editable), so the
# runtime needs no source tree and no uv.
COPY cdeclient/README.md /app/cdeclient/README.md
COPY cdeclient/src/ /app/cdeclient/src/
COPY api/README.md ./README.md
COPY api/src/ ./src/
RUN uv sync --frozen --no-dev --no-editable

COPY --from=data /app/warehouse/openhydra.duckdb /app/warehouse/openhydra.duckdb
COPY --from=web /app/web/dist /app/web/dist

# Run as a user without privileges. The app only reads its files.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app

ENV OPENHYDRA_DUCKDB=/app/warehouse/openhydra.duckdb \
    OPENHYDRA_STATIC_DIR=/app/web/dist \
    PATH="/app/api/.venv/bin:$PATH"
EXPOSE 8000
# Railway sets $PORT. `exec` makes uvicorn PID 1, so it gets SIGTERM directly
# and stops cleanly. The app writes its own JSON access log.
CMD ["/bin/sh", "-c", "exec uvicorn openhydra_api.main:app --host 0.0.0.0 --port \"${PORT:-8000}\" --no-access-log"]
