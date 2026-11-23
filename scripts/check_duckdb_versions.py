"""Fail when the DuckDB that writes the warehouse differs from the one that reads it.

dbt (warehouse/uv.lock) writes openhydra.duckdb in the image, and the API
(api/uv.lock) reads it. A newer writer can use a storage format that the older
reader cannot open, which stops the deploy at its health check.

Usage: python3 scripts/check_duckdb_versions.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def duckdb_version(lock: Path) -> str:
    data = tomllib.loads(lock.read_text())
    for pkg in data.get("package", []):
        if pkg.get("name") == "duckdb":
            return str(pkg["version"])
    raise SystemExit(f"{lock}: no duckdb package")


def main() -> None:
    writer = duckdb_version(ROOT / "warehouse" / "uv.lock")
    reader = duckdb_version(ROOT / "api" / "uv.lock")
    analysis = duckdb_version(ROOT / "analysis" / "uv.lock")
    print(f"duckdb: warehouse (writer) {writer}, api (reader) {reader}, analysis {analysis}")
    if writer != reader:
        sys.exit("The warehouse and the API lock different DuckDB versions. Lock the same one.")
    if analysis.split(".")[0] != reader.split(".")[0]:
        sys.exit("The notebook locks another DuckDB major version than the warehouse file.")


if __name__ == "__main__":
    main()
