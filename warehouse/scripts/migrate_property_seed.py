"""One-time migration: add the year column to the property seed.

The seed came from one request per area and offense over 01-2015 to 12-2024,
so its values are totals over that window. The new column is null for these
rows, which means "a total over the whole window". A new extract fills it.

Usage: uv run python scripts/migrate_property_seed.py ../deploy/seed/property.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

from openhydra_etl.normalize import PROPERTY_SCHEMA


def main(path: str) -> None:
    src = Path(path)
    frame = pl.read_parquet(src)
    if "year" in frame.columns:
        print("already migrated")
        return
    out = frame.with_columns(pl.lit(None, dtype=pl.Int32).alias("year")).select(
        list(PROPERTY_SCHEMA)
    )
    tmp = src.with_suffix(".parquet.tmp")
    out.write_parquet(tmp)
    tmp.replace(src)
    print(f"{src}: {out.height} rows, columns {out.columns}")


if __name__ == "__main__":
    main(sys.argv[1])
