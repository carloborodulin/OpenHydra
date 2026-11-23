# api: the OpenHydra service

A read-only **FastAPI** service. It serves the DuckDB warehouse marts and
proxies live agency data from the FBI CDE API. The browser talks only to this
service, so the API key stays on the server.

```
warehouse/openhydra.duckdb (marts) ──▶ FastAPI (read-only) ──▶ JSON ──▶ web/
FBI CDE API ──▶ live agency routes (checked, cached, limited) ──▶ JSON ──▶ web/
```

## Run

From the repository root, `make data` builds the warehouse and `make serve`
starts the service. Or, in this directory:

```bash
uv sync --frozen
uv run oh-api        # http://127.0.0.1:8000  (docs at /docs)
```

The service reads `warehouse/openhydra.duckdb`. Set `OPENHYDRA_DUCKDB` to use
another file, and `OPENHYDRA_STATIC_DIR` to serve the built dashboard at `/`.
The live routes need `FBI_CDE_API_KEY`. The client reads it from the
environment or from the root `.env` file.

## Warehouse routes

| Method and path | Returns |
|---|---|
| `GET /health` | Readiness: the warehouse opens and has rows. |
| `GET /api/meta` | Offenses, states, levels, the arrest taxonomy and the arrest categories. |
| `GET /api/offenses/monthly?offense=&level=&area=` | The monthly offense and clearance series, with TTM, YoY and the 2019 index. |
| `GET /api/offenses/benchmark?offense=&level=&area=` | A state series next to the national series. |
| `GET /api/agencies?state=` | Agencies with coordinates and NIBRS adoption. |
| `GET /api/arrests?level=&area=&offense=&category=` | Arrest breakdowns for one offense (default `all`). |
| `GET /api/arrests/available?level=&area=` | The arrest offenses with rows for one scope. |
| `GET /api/police-employment?level=&area=` | Law enforcement employment by year. |
| `GET /api/population?level=&area=` | Census population by year. |
| `GET /api/hate-crime?level=&area=&category=` | Hate crime breakdowns. |
| `GET /api/shr?level=&area=&category=` | Supplementary homicide breakdowns. |
| `GET /api/property?level=&area=&offense=&category=` | Expanded property breakdowns. |
| `GET /api/nibrs?level=&area=&offense=&category=` | NIBRS breakdowns. |
| `GET /api/nibrs-estimation?level=&area=&offense=&category=` | NIBRS estimates. |
| `GET /api/lesdc?chart_type=&year=&section=` | Law enforcement suicide data. |
| `GET /api/uof/participation` | Use-of-force participation by year. |
| `GET /api/uof/questions?year=&category=` | Use-of-force question totals. |

## Live agency routes

| Method and path | Upstream |
|---|---|
| `GET /api/agency/{ori}/offenses?offense=` | `/summarized/agency/{ori}/{offense}` |
| `GET /api/agency/{ori}/arrests?offense=&category=` | `/arrest/agency/{ori}/{code}` (a rollup sums 4 codes) |
| `GET /api/agency/{ori}/police-employment` | `/pe/{ST}/{ori}` |
| `GET /api/agency/{ori}/hate-crime?category=` | `/hate-crime/agency/{ori}` |
| `GET /api/agency/{ori}/shr?category=` | `/shr/agency/{ori}` |
| `GET /api/agency/{ori}/property?offense=&category=` | `/supplemental/agency/{ori}/{offense}` |
| `GET /api/agency/{ori}/nibrs?offense=&category=` | `/nibrs/agency/{ori}/{code}` |

Before an upstream call, each route checks its input:

- The ORI must have 9 characters (else 422) and must be in the agency list (else 404).
- The offense must be in the API's own list (else 422).

The cache keeps the unfiltered rows for one hour and a valid empty result for
five minutes. Concurrent requests for one key make one upstream call. Only a
cache miss counts against the limits:

| Limit | Default | Variable | Answer |
|---|---|---|---|
| Per client | 30 per minute | `OPENHYDRA_LIVE_CLIENT_PER_MIN` | 429 `rate_limited` |
| All clients | 600 per hour | `OPENHYDRA_LIVE_GLOBAL_PER_HOUR` | 503 `live_budget_spent` |
| Concurrent calls | 4 | `OPENHYDRA_LIVE_CONCURRENCY` | 503 `live_busy` |

### Errors

An upstream failure is never an empty list. The body is
`{"detail": "...", "code": "...", "request_id": "..."}` with
`Cache-Control: no-store`.

| Cause | Status | `code` |
|---|---|---|
| No API key on the server | 503 | `live_data_unconfigured` |
| The key is rejected | 503 | `upstream_auth` |
| Upstream rate limit | 503 + `Retry-After` | `upstream_rate_limited` |
| Upstream timeout | 504 | `upstream_timeout` |
| Upstream 404, 5xx or connection failure | 502 | `upstream_error` |
| Upstream body is not valid | 502 | `upstream_bad_response` |

## Logs

Each response has an `X-Request-ID` header. The service writes one JSON line per
request on stdout: the request ID, the method, the route template, the status,
the duration, the cache result and the upstream status class. No log line holds
the API key.

## Develop

```bash
uv run --frozen pytest      # TestClient against temp DuckDB fixtures (no warehouse needed)
uv run --frozen ruff check
uv run --frozen mypy
```
