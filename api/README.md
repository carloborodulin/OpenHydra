# api — OpenHydra service

A read-only **FastAPI** service over the DuckDB warehouse marts. The browser
talks to this service, never to the upstream FBI API, so the API key is never
exposed.

```
warehouse/openhydra.duckdb (marts) ──▶ FastAPI (read-only) ──▶ JSON ──▶ web/ (Phase 5)
```

## Run

```bash
cd api
uv sync
uv run oh-api        # http://127.0.0.1:8000  (docs at /docs)
```

Reads `warehouse/openhydra.duckdb` (override with `OPENHYDRA_DUCKDB`). Build the
warehouse first — see [../warehouse](../warehouse).

## Endpoints

| method · path | returns |
|---|---|
| `GET /health` | service + row-count check |
| `GET /api/meta` | available offenses, states, levels |
| `GET /api/offenses/monthly?offense=&level=&area=` | monthly offense/clearance series |
| `GET /api/agencies?state=` | geocoded agencies + NIBRS adoption |
| `GET /api/arrests?level=&area=&category=` | arrest demographic breakdowns |
| `GET /api/police-employment?level=&area=` | employment by year |

Interactive OpenAPI docs are auto-generated at `/docs`.

## Develop

```bash
uv run pytest      # TestClient against a temp DuckDB fixture (no warehouse needed)
uv run ruff check
uv run mypy
```
