# OpenHydra — single-service image: FastAPI serves the API + the built dashboard.
# 3 stages: build the web → build the DuckDB marts (dbt) from seed parquet →
# assemble the API runtime.

# ---- 1. build the dashboard ------------------------------------------------
FROM node:22-slim AS web
WORKDIR /app/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build      # -> /app/web/dist

# ---- 2. build the DuckDB marts from the committed seed parquet -------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS data
WORKDIR /app
COPY warehouse/ ./warehouse/
COPY deploy/seed/ ./data/raw/
WORKDIR /app/warehouse/dbt
# dbt reads ../../data/raw/*.parquet (relative to CWD) and writes ../openhydra.duckdb
RUN uvx --from "dbt-duckdb>=1.8" dbt build --profiles-dir .

# ---- 3. API runtime --------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS final
WORKDIR /app/api
COPY api/ ./
RUN uv sync --frozen --no-dev
COPY --from=data /app/warehouse/openhydra.duckdb /app/warehouse/openhydra.duckdb
COPY --from=web /app/web/dist /app/web/dist
ENV OPENHYDRA_DUCKDB=/app/warehouse/openhydra.duckdb \
    OPENHYDRA_STATIC_DIR=/app/web/dist
EXPOSE 8000
# Railway injects $PORT; bind all interfaces.
CMD uv run --no-dev uvicorn openhydra_api.main:app --host 0.0.0.0 --port ${PORT:-8000}
