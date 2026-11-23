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

## Pull data and publish a release

An extract never writes over the published data. It runs in two steps.

**1. Pull into a staging directory.**

```bash
# bounded example: national + NY, two domains
uv run oh-etl pull --states NY --domains summarized,arrests --from 01-2020 --to 12-2022

# full pull: all 50 states + DC, all 10 offenses, all 11 domains (the default)
uv run oh-etl pull --states all
```

- Each run writes to `data/staging/<run id>/` (git ignores it).
- One part file is written per upstream request, and the domain file only after every part succeeds.
- `_manifest.json` records the window, the states and the outcome of each request (ok, empty or error).
- A failed domain is listed and the command exits with status 2. Run the same command with `--out data/staging/<run id>` to resume: the parts that exist are not fetched again.
- `--per-hour` limits the request rate (default 700 per hour), so the live site keeps part of the key quota.

**2. Promote the run to the release in `deploy/seed/`.**

```bash
uv run oh-etl promote data/staging/<run id> --dry-run   # check and report only
uv run oh-etl promote data/staging/<run id>
```

`promote` works in this order:

- A domain that the run completed replaces the domain in the release. With `--merge`, it replaces only the partitions it holds (use this for a subset pull, for example one state).
- A domain that the run did not complete stays as it was. A failed UoF request, for example, keeps the last good UoF data.
- A domain may not lose a partition (a state, an offense or a year) unless you pass `--allow-shrink`.
- `revisions.md` lists the changed values against the last release.
- The new files and `_manifest.json` replace `deploy/seed/` in one rename.

Then `make data` at the repository root builds the warehouse from the release. The dashboard shows the release ID, the window and the extraction date of each view.

The extract needs `FBI_CDE_API_KEY`. The client reads it from the environment
or from the root `.env` file. You do not need an extract to build the
warehouse: `make data` uses the committed release.

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
