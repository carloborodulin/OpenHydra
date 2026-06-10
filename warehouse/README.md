# warehouse — OpenHydra ETL

Pulls FBI CDE data via [`cdeclient`](../cdeclient) and lands it as tidy
**long-format Parquet** under `data/raw/`, ready for the dbt → DuckDB layer.

```
cdeclient ──extract──▶ data/raw/{summarized,agencies,arrests,pe}.parquet ──▶ dbt/duckdb (next)
```

## Install (dev)

```bash
cd warehouse
uv sync           # installs deps + cdeclient (path dependency)
```

## Pull data

```bash
# bounded example: national + NY, two offenses
uv run oh-etl pull --states NY --offenses homicide,violent-crime --from 01-2020 --to 12-2022

# full pull: all 50 states + DC, all 10 offenses, all domains
uv run oh-etl pull --states all
```

Needs `FBI_CDE_API_KEY` (from the repo `.env`). `data/raw/` is git-ignored.

## Develop

```bash
uv run pytest      # normalize tests run against ../data/samples (no network)
uv run ruff check
uv run mypy
```

## Tidy tables (long format)

| domain | grain | columns |
|---|---|---|
| `summarized` | level × area × offense × series × measure × month | `level, area, offense, series(offenses/clearances), measure(rate/actual), period(date), value` |
| `agencies` | ORI | `ori, agency_name, agency_type, county, state_abbr, state_name, latitude, longitude, is_nibrs, nibrs_start_date` |
| `arrests` | level × area × breakdown × label | `level, area, category, label, value` |
| `pe` | level × area × section × metric × year | `level, area, section(rate/actual), metric, year, value` |
| `hate_crime` | level × area × dimension × label | `level, area, category, label, value` |
