"""Filesystem locations for the warehouse (overridable via env)."""

from __future__ import annotations

import os
from pathlib import Path

# config.py -> openhydra_etl -> src -> warehouse -> <repo root>
REPO_ROOT = Path(__file__).resolve().parents[3]

RAW_DIR = Path(os.getenv("OPENHYDRA_RAW_DIR", REPO_ROOT / "data" / "raw"))
DUCKDB_PATH = Path(os.getenv("OPENHYDRA_DUCKDB", REPO_ROOT / "warehouse" / "openhydra.duckdb"))
# Each extract run writes to its own directory here (git ignores it).
STAGING_DIR = Path(os.getenv("OPENHYDRA_STAGING_DIR", REPO_ROOT / "data" / "staging"))
# The published release: the committed seed that the image and `make data` build.
RELEASE_DIR = Path(os.getenv("OPENHYDRA_RELEASE_DIR", REPO_ROOT / "deploy" / "seed"))
