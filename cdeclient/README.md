# cdeclient

A small, typed Python client for the **FBI Crime Data Explorer (CDE) API**, with
retries, pydantic models, and a `cde` CLI. This is the foundation layer of
[OpenHydra](../README.md) — the ETL, API, and dashboard all build on it.

## Install (dev)

```bash
cd cdeclient
uv sync          # creates .venv, installs deps (Python pinned to 3.12)
```

## Use as a library

```python
from cdeclient import CdeClient, Offense

with CdeClient() as cde:                      # reads FBI_CDE_API_KEY from env/.env
    agencies = cde.agencies_by_state("NY")    # {county: [Agency, ...]}
    homicide = cde.summarized_national(Offense.HOMICIDE, "01-2020", "12-2022")
    print(homicide.offenses.rates["United States Offenses"])
```

## Use as a CLI

```bash
uv run cde agencies NY
uv run cde summarized national homicide --from 01-2020 --to 12-2022
uv run cde summarized state NY violent-crime --from 01-2020 --to 12-2022
uv run cde arrests national --type totals --from 01-2020 --to 12-2022
uv run cde pe national --from 2018 --to 2022      # note: /pe uses YEARS
```

## Develop

```bash
uv run pytest      # tests run against the JSON in ../data/samples (no network)
uv run ruff check
uv run mypy
```

## Notes

- Most endpoints take `MM-YYYY`; `/pe` takes 4-digit years. The client normalizes
  both (you can pass `"2020-01"`, `"01-2020"`, or a `datetime.date`).
- The API gateway intermittently returns `503`; the client retries with backoff.
