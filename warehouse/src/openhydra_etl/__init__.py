"""OpenHydra ETL — pull FBI CDE data into a DuckDB/Parquet warehouse."""

from __future__ import annotations

from .extract import Extractor

__all__ = ["Extractor"]
__version__ = "0.1.0"
