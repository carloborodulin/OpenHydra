"""Fail when the lock holds more than one DuckDB version.

dbt writes openhydra.duckdb in the image and the API reads it. A newer writer
can use a storage format that an older reader cannot open, which stops the
deploy at its health check. The uv workspace has one lock (uv.lock), so one
DuckDB version serves the writer, the reader and the notebook. This check
keeps it that way (a marker-specific fork would add a second version).

Usage: python3 scripts/check_duckdb_versions.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    lock = tomllib.loads((ROOT / "uv.lock").read_text())
    versions = sorted({p["version"] for p in lock.get("package", []) if p.get("name") == "duckdb"})
    print(f"duckdb in uv.lock: {', '.join(versions) or 'none'}")
    if len(versions) != 1:
        sys.exit("The workspace must lock exactly one DuckDB version.")


if __name__ == "__main__":
    main()
