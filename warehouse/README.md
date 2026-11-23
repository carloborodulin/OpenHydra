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
# bounded example: national + NY, two domains
uv run oh-etl pull --states NY --domains summarized,arrests --from 01-2020 --to 12-2022

# full pull: all 50 states + DC, all 10 offenses, all 11 domains (the default)
uv run oh-etl pull --states all
```

The extract needs `FBI_CDE_API_KEY`. The client reads it from the environment
or from the root `.env` file. The files go to `data/raw/`, which git ignores.

You do not need an extract to build the warehouse: `make data` at the
repository root uses the committed snapshot in `deploy/seed/`.

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
| `arrests` | level × area × arrest code × breakdown × label | `level, area, offense, arrest_code, window_from, window_to, category, label, value` |
| `pe` | level × area × section × metric × year | `level, area, section(rate/actual), metric, year, value` |
| `hate_crime` | level × area × dimension × label | `level, area, category, label, value` |
| `shr` | level × area × section_dimension × label | `level, area, category, label, value` |
| `property` | level × area × offense × dimension × label | `level, area, offense, category, label, value` |
| `nibrs` | level × area × offense × section_dimension × label | `level, area, offense, category, label, value` |
| `lesdc` | year × chart_type × section × label (national) | `year, chart_type, section, label, value` |
| `uof_participation` | year (national) | `year, participating_agencies, total_agencies, participation_percent` |
| `uof_questions` | year × quest × item (national) | `year, category, label, value` |
| `nibrs_estimation` | level × area × offense × section_dimension × label (national+region) | `level, area, offense, category, label, value` |
