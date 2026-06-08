"""Filesystem locations for the warehouse (overridable via env)."""

from __future__ import annotations

import os
from pathlib import Path

# config.py -> openhydra_etl -> src -> warehouse -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = Path(os.getenv("OPENHYDRA_RAW_DIR", REPO_ROOT / "data" / "raw"))
DUCKDB_PATH = Path(os.getenv("OPENHYDRA_DUCKDB", REPO_ROOT / "warehouse" / "openhydra.duckdb"))
