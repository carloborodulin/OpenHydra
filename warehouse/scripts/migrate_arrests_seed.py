"""One-time migration of the arrests seed to the canonical arrest schema.

The old extract wrote the code "all" response twice: as violent-crime and as
property-crime. Both labels were wrong, because code "all" is every offense.
This script keeps one copy as offense "all", drops the other, and adds the
arrest_code and window columns. The seed window was 01-2015 to 12-2024.

Usage: uv run python scripts/migrate_arrests_seed.py ../deploy/seed/arrests.parquet
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
from cdeclient.constants import ARREST_OFFENSES

from openhydra_etl.normalize import ARRESTS_SCHEMA

WINDOW = ("01-2015", "12-2024")


def migrate(frame: pl.DataFrame) -> pl.DataFrame:
    if "arrest_code" in frame.columns:
        return frame  # already migrated
    a = frame.filter(pl.col("offense") == "violent-crime").drop("offense")
    b = frame.filter(pl.col("offense") == "property-crime").drop("offense")
    keys = ["level", "area", "category", "label"]
    if a.sort(keys).equals(b.sort(keys)) is False:
        raise SystemExit("violent-crime and property-crime rows differ; refusing to migrate")
    kept = frame.filter(pl.col("offense") != "property-crime").with_columns(
        pl.when(pl.col("offense") == "violent-crime")
        .then(pl.lit("all"))
        .otherwise(pl.col("offense"))
        .alias("offense")
    )
    codes = {slug: info.code for slug, info in ARREST_OFFENSES.items()}
    unknown = set(kept["offense"].unique()) - set(codes)
    if unknown:
        raise SystemExit(f"unknown arrest slugs in seed: {sorted(unknown)}")
    out = kept.with_columns(
        pl.col("offense").replace_strict(codes).alias("arrest_code"),
        pl.lit(WINDOW[0]).alias("window_from"),
        pl.lit(WINDOW[1]).alias("window_to"),
    )
    return out.select(list(ARRESTS_SCHEMA)).cast(ARRESTS_SCHEMA)  # type: ignore[arg-type]


def main(path: str) -> None:
    src = Path(path)
    before = pl.read_parquet(src)
    after = migrate(before)
    tmp = src.with_suffix(".parquet.tmp")
    after.write_parquet(tmp)
    tmp.replace(src)
    print(f"{src}: {before.height} -> {after.height} rows")
    print(after.group_by("offense").len().sort("offense"))


if __name__ == "__main__":
    main(sys.argv[1])
