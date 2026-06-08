"""Orchestrates CDE API calls and lands tidy Parquet under data/raw/."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
from cdeclient import CdeClient
from cdeclient.constants import Offense

from . import normalize
from .config import RAW_DIR

ALL_OFFENSES: list[str] = [o.value for o in Offense]


def _year(month: str | date) -> str:
    """Extract the 4-digit year from an 'MM-YYYY' string (for /pe)."""
    return str(month).split("-")[-1]


class Extractor:
    """Pulls CDE data via :class:`cdeclient.CdeClient` and writes Parquet.

    One Parquet file per domain under ``raw_dir`` (overwritten each run).
    """

    def __init__(self, client: CdeClient, raw_dir: Path = RAW_DIR) -> None:
        self.client = client
        self.raw_dir = raw_dir
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def _write(self, domain: str, frame: pl.DataFrame) -> Path:
        path = self.raw_dir / f"{domain}.parquet"
        frame.write_parquet(path)
        return path

    def pull_summarized(
        self,
        offenses: list[str],
        states: list[str],
        from_: str,
        to: str,
        *,
        include_national: bool = True,
    ) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        if include_national:
            for off in offenses:
                resp = self.client.summarized_national(off, from_, to)
                frames.append(
                    normalize.summarized_to_frame(resp, level="national", area="US", offense=off)
                )
        for st in states:
            for off in offenses:
                resp = self.client.summarized_state(st, off, from_, to)
                frames.append(
                    normalize.summarized_to_frame(resp, level="state", area=st, offense=off)
                )
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.SUMMARIZED_SCHEMA)
        self._write("summarized", frame)
        return frame

    def pull_agencies(self, states: list[str]) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        for st in states:
            frames.append(normalize.agencies_to_frame(self.client.agencies_by_state(st)))
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.AGENCIES_SCHEMA)
        self._write("agencies", frame)
        return frame

    def pull_arrests(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        if include_national:
            resp = self.client.arrests_national("all", from_=from_, to=to)
            frames.append(normalize.arrests_to_frame(resp, level="national", area="US"))  # type: ignore[arg-type]
        for st in states:
            resp = self.client.arrests_state(st, "all", from_=from_, to=to)
            frames.append(normalize.arrests_to_frame(resp, level="state", area=st))  # type: ignore[arg-type]
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.ARRESTS_SCHEMA)
        self._write("arrests", frame)
        return frame

    def pull_pe(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        fy, ty = _year(from_), _year(to)
        if include_national:
            frames.append(
                normalize.pe_to_frame(
                    self.client.police_employment_national(fy, ty), level="national", area="US"
                )
            )
        for st in states:
            frames.append(
                normalize.pe_to_frame(
                    self.client.police_employment_state(st, fy, ty), level="state", area=st
                )
            )
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.PE_SCHEMA)
        self._write("pe", frame)
        return frame
