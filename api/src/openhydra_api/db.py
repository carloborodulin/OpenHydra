"""DuckDB access — a read-only connection per request (FastAPI dependency)."""

from __future__ import annotations

from collections.abc import Iterator

import duckdb

from .config import duckdb_path


def get_conn() -> Iterator[duckdb.DuckDBPyConnection]:
    con = duckdb.connect(str(duckdb_path()), read_only=True)
    try:
        yield con
    finally:
        con.close()
