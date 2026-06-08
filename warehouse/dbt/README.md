# dbt — OpenHydra warehouse models

Transforms the long-format Parquet from `oh-etl pull` into a DuckDB warehouse:
**sources (Parquet) → staging (views) → marts (tables)**.

```
data/raw/*.parquet ──source──▶ stg_* (views) ──▶ {fct_offenses_monthly,
                                                   dim_agencies,
                                                   fct_arrests,
                                                   fct_police_employment}
```

## Run

```bash
cd warehouse
uv sync --group dbt                  # installs dbt-duckdb (heavy; on demand)
cd dbt
uv run --group dbt dbt build --profiles-dir .   # run models + tests
```

Output lands in `warehouse/openhydra.duckdb` (git-ignored). Inspect:

```bash
uv run --group dbt python -c "import duckdb; \
  print(duckdb.connect('../openhydra.duckdb').sql('select * from fct_offenses_monthly limit 5'))"
```

## Marts

| model | grain | notes |
|---|---|---|
| `fct_offenses_monthly` | level × area × offense × month | offense/clearance rate & actual, `clearance_ratio` |
| `dim_agencies` | ORI | deduped; `nibrs_start_year` derived |
| `fct_arrests` | level × area × category × label | demographic breakdowns |
| `fct_police_employment` | level × area × section × metric × year | staffing (sparse) |

Sources read `../../data/raw/*.parquet`, so run dbt from this directory.
