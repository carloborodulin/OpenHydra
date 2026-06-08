"""Locating the DuckDB warehouse (overridable via env)."""

from __future__ import annotations

import os
from pathlib import Path

# config.py -> openhydra_api -> src -> api -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DUCKDB = REPO_ROOT / "warehouse" / "openhydra.duckdb"


def duckdb_path() -> Path:
    """Path to the warehouse DuckDB file (env override: OPENHYDRA_DUCKDB)."""
    return Path(os.getenv("OPENHYDRA_DUCKDB", str(DEFAULT_DUCKDB)))
