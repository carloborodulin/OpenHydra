"""Add the optional columns of the current schema to the files of a release.

A schema change adds a nullable column (for example the NIBRS estimate
interval). The files of the committed release do not have it, and dbt selects
it. This script adds each missing optional column as nulls, in place.

Usage: uv run python scripts/conform_seed.py ../deploy/seed
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

from openhydra_etl.snapshot import FILES, _conform, write_parquet_atomic


def main(target: str) -> None:
    root = Path(target)
    for spec in FILES.values():
        path = root / spec.file
        frame = pl.read_parquet(path)
        out = _conform(frame, spec)
        if out.columns != frame.columns:
            write_parquet_atomic(out, path)
            print(f"{spec.file}: added {sorted(set(out.columns) - set(frame.columns))}")


if __name__ == "__main__":
    main(sys.argv[1])
