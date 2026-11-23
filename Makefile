# OpenHydra tasks. A fresh clone needs only uv and Node.js: no FBI API key.
#
#   make setup   Install the locked Python and web dependencies.
#   make data    Build the DuckDB warehouse from the committed seed.
#   make web     Build the dashboard into web/dist.
#   make serve   Serve the API and the dashboard on http://127.0.0.1:$(PORT).
#   make smoke   Start the server, check the main routes, then stop it.
#   make check   Run all linters, type checks and tests.
#   make notebook  Run the analysis notebook (writes analysis/outputs).
#
# Run `make setup data web serve` the first time.

PORT ?= 8000
SEED := deploy/seed
RAW := data/raw
NODE_OPTIONS ?= --max-old-space-size=2048
export NODE_OPTIONS

.PHONY: setup data web serve smoke check notebook clean

setup:
	cd cdeclient && uv sync --frozen
	cd warehouse && uv sync --frozen --group dbt
	cd api && uv sync --frozen
	cd analysis && uv sync --frozen
	cd web && npm ci

# dbt reads data/raw/*.parquet and data/seeds/population.csv, and writes
# warehouse/openhydra.duckdb.
data:
	mkdir -p $(RAW)
	cp $(SEED)/*.parquet $(SEED)/_manifest.json $(RAW)/
	cd warehouse && uv sync --frozen --group dbt
	cd warehouse/dbt && ../.venv/bin/dbt build --profiles-dir .

web:
	cd web && npm run build

serve:
	@test -f warehouse/openhydra.duckdb || { echo "Run 'make data' first."; exit 1; }
	@test -d web/dist || { echo "Run 'make web' first."; exit 1; }
	OPENHYDRA_STATIC_DIR=$(CURDIR)/web/dist \
	  api/.venv/bin/uvicorn openhydra_api.main:app --app-dir api/src \
	  --host 127.0.0.1 --port $(PORT) --no-access-log

# Start the server in the background, wait for /health, check the routes that
# need no API key, and always stop the server.
smoke:
	@test -f warehouse/openhydra.duckdb || { echo "Run 'make data' first."; exit 1; }
	@OPENHYDRA_STATIC_DIR=$(CURDIR)/web/dist \
	  api/.venv/bin/uvicorn openhydra_api.main:app --app-dir api/src \
	  --host 127.0.0.1 --port $(PORT) --no-access-log > /dev/null 2>&1 & \
	pid=$$!; trap 'kill $$pid 2>/dev/null' EXIT; \
	curl -sf --retry 30 --retry-delay 1 --retry-connrefused -o /dev/null http://127.0.0.1:$(PORT)/health && \
	for path in /health /api/meta "/api/offenses/monthly?offense=violent-crime" /api/arrests/available; do \
	  code=$$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$(PORT)$$path"); \
	  echo "$$code $$path"; test "$$code" = 200 || exit 1; \
	done

check:
	cd cdeclient && uv run --frozen ruff check && uv run --frozen ruff format --check && uv run --frozen mypy && uv run --frozen pytest -q
	cd warehouse && uv run --frozen ruff check && uv run --frozen ruff format --check && uv run --frozen mypy && uv run --frozen pytest -q
	cd api && uv run --frozen ruff check && uv run --frozen ruff format --check && uv run --frozen mypy && uv run --frozen pytest -q
	cd web && npm run lint && npm run build

notebook:
	cd analysis && uv run --frozen python notebooks/01_crime_trends.py

clean:
	rm -rf $(RAW) warehouse/openhydra.duckdb web/dist
