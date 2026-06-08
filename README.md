# OpenHydra

An end-to-end crime-data analytics platform built on the **FBI Crime Data
Explorer (CDE) API** — the FBI's public Uniform Crime Reporting (UCR) data for
the United States. Ingest → store → analyze → serve → visualize.

- API docs: https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi
- Get a key: https://api.data.gov/signup/

> **Status:** Phase 1 complete — `cdeclient` (typed Python client + CLI) is
> built, tested, and lint/type-clean, with CI. Phase 2 (ETL → warehouse) is next.
> The API surface below is verified against the live API.

## Architecture

```
web/        React + Vite + TS dashboard (MapLibre GL map, Recharts)   ← frontend / dataviz
   │ REST/JSON
api/        FastAPI service over the warehouse (no API key in browser) ← backend
   │ reads
warehouse/  DuckDB + Parquet, transformed with dbt                     ← data engineering
notebooks/  COVID-spike / clearance-rate / demographics analysis       ← data science
   │ ETL writes
cdeclient/  typed Python client + CLI (retries, pydantic models)       ← SWE / packaging
   │ HTTP
FBI Crime Data Explorer API
```

## Tech stack

| Layer | Choice |
|---|---|
| Tooling | **uv** (env + packaging), **ruff** (lint/format), **mypy**, **pytest** |
| Client (`cdeclient`) | **httpx** · **pydantic v2** · **tenacity** (retries) · **Typer** (CLI) |
| Warehouse | **DuckDB** + **Parquet**, transforms via **dbt** (`dbt-duckdb`) |
| Analysis | **Jupyter** + **Polars** + **Plotly** |
| Backend | **FastAPI** + **uvicorn** |
| Frontend | **React** + **Vite** + **TypeScript**, TanStack Query, Tailwind, **Recharts**, **MapLibre GL** |
| Infra | **Docker Compose**, **GitHub Actions** CI, deploy on **Railway** |

Python is pinned to **3.12** via uv (the system Python is 3.14 — kept off the
critical path for wheel stability).

## Roadmap

- [x] **Phase 0** — API key, git, `explore.sh`, samples, verified API reference
- [x] **Phase 1** — `cdeclient`: typed client + CLI, retries, 20 tests, strict mypy, CI
- [ ] **Phase 2** — ETL → DuckDB/Parquet warehouse (dbt models)
- [ ] **Phase 3** — analysis notebooks + narrative
- [ ] **Phase 4** — FastAPI service
- [ ] **Phase 5** — React/MapLibre dashboard, deployed to Railway
- [ ] **Phase 6** — polish: docs, screenshots, live demo, green CI

## Setup

The API key lives in `.env` (git-ignored). Copy the template and add your key:

```bash
cp .env.example .env   # then edit FBI_CDE_API_KEY
```

## Pull sample data

```bash
./explore.sh
```

Hits one endpoint per family and writes JSON into `data/samples/` (plus
`data/samples/_manifest.tsv`). Retries through the gateway's intermittent `503`s.

## API reference (verified)

- **Base URL:** `https://api.usa.gov/crime/fbi/cde`
- **Auth:** append `?API_KEY=<key>` (query param) to every request
- **Returns:** JSON (read-only)
- **Date params:** most endpoints use **`MM-YYYY`** (e.g. `from=01-2020&to=12-2022`).
  The Police Employment (`/pe`) endpoints use **4-digit years** (`from=2018&to=2022`).

### Working endpoint families

| Family | Example path | Data shape |
|---|---|---|
| **Agencies** | `/agency/byStateAbbr/{ST}` | Object keyed by county → array of agencies. Each: `ori`, `agency_name`, `agency_type_name`, `latitude`, `longitude`, `is_nibrs`, `nibrs_start_date`, `counties`, `state_abbr`. (NY = 537 agencies.) **Geocoded → mapping.** |
| **Summarized** | `/summarized/{national\|state/{ST}\|agency/{ori}}/{offense}` | `offenses.rates` + `offenses.actuals`, each `{series → {MM-YYYY → value}}` with "…Offenses" and "…Clearances" series; plus `populations` (population + participated_population) and `cde_properties`. **Time-series / trends.** |
| **Arrests** | `/arrest/{national\|state/{ST}}/{offense}?type={totals\|counts}` | `type=totals` → demographic breakdowns (`Arrestee Sex`, `Arrestee Race`, `Male/Female Arrests By Age`, `Offense Name/Category/Breakdown`). `type=counts` → monthly `rates`/`actuals` time series. **Demographics + trends.** |
| **Police Employment** | `/pe/{national\|state/{ST}}?from=YYYY&to=YYYY` | `rates` (LE employees per 1,000) + `actuals` (Male/Female Officers/Civilians) by year. ⚠️ Many cells are `null` — coverage is sparse for recent years. |

### Verified offense slugs (summarized)

`violent-crime`, `homicide`, `rape`, `robbery`, `aggravated-assault`,
`property-crime`, `burglary`, `larceny`, `motor-vehicle-theft`, `arson`
(hyphenated, not `snake_case`).

### Known gaps / not found on this base

- `/estimate/*` and `/nibrs/*` incident-level demographics → `404` on the `cde`
  base with every path variant tried. They appear to live on the legacy `sapi`
  base / deprecated Swagger UI (`https://crime-data-api.fr.cloud.gov/swagger-ui/`).
  Revisit if the project needs national estimates or incident-level NIBRS data.

## Layout

```
.env(.example)        API key + base URL (key is git-ignored)
explore.sh            pulls one sample per endpoint family
data/samples/         saved JSON responses + _manifest.tsv
cdeclient/            typed Python client library + CLI  (Phase 1)
```
