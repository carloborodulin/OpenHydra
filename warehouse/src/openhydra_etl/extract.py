"""Orchestrates CDE API calls and lands tidy Parquet under data/raw/."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl
from cdeclient import CdeClient
from cdeclient.constants import ARREST_OFFENSES, EXPANDED_PROPERTY_OFFENSES, Offense, arrest_code

from . import normalize
from .config import RAW_DIR

ALL_OFFENSES: list[str] = [o.value for o in Offense]
# All 48 arrest offense slugs (the full `arrest_offense` taxonomy).
ALL_ARREST_OFFENSES: list[str] = list(ARREST_OFFENSES)


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
        self,
        states: list[str],
        offenses: list[str],
        from_: str,
        to: str,
        *,
        include_national: bool = True,
    ) -> pl.DataFrame:
        # Arrests take a numeric offense code, a different taxonomy from the
        # offense slugs. Resolve slug -> code (arrest slug, summarized slug, or a
        # raw code); offenses sharing a code (e.g. the aggregates -> "all") are
        # fetched once per area, then a frame is emitted per slug (keyed on the
        # slug the rest of the app uses).
        codes: dict[str, str] = {off: arrest_code(off) for off in offenses}

        def _per_area(fetch, level: str, area: str) -> list[pl.DataFrame]:  # type: ignore[no-untyped-def]
            by_code: dict[str, object] = {}
            out: list[pl.DataFrame] = []
            for off, code in codes.items():
                resp = by_code.setdefault(code, fetch(code))
                out.append(
                    normalize.arrests_to_frame(resp, level=level, area=area, offense=off)  # type: ignore[arg-type]
                )
            return out

        frames: list[pl.DataFrame] = []
        if include_national:
            frames += _per_area(
                lambda code: self.client.arrests_national(code, from_=from_, to=to),
                "national",
                "US",
            )
        for st in states:
            frames += _per_area(
                lambda code, st=st: self.client.arrests_state(st, code, from_=from_, to=to),
                "state",
                st,
            )
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.ARRESTS_SCHEMA)
        self._write("arrests", frame)
        return frame

    def pull_hate_crime(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        if include_national:
            frames.append(
                normalize.hate_crime_to_frame(
                    self.client.hate_crime_national(from_, to), level="national", area="US"
                )
            )
        for st in states:
            frames.append(
                normalize.hate_crime_to_frame(
                    self.client.hate_crime_state(st, from_, to), level="state", area=st
                )
            )
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.HATE_CRIME_SCHEMA)
        self._write("hate_crime", frame)
        return frame

    def pull_shr(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        if include_national:
            frames.append(
                normalize.shr_to_frame(
                    self.client.shr_national(from_, to), level="national", area="US"
                )
            )
        for st in states:
            frames.append(
                normalize.shr_to_frame(self.client.shr_state(st, from_, to), level="state", area=st)
            )
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.SHR_SCHEMA)
        self._write("shr", frame)
        return frame

    def pull_property(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        offenses = list(EXPANDED_PROPERTY_OFFENSES)
        frames: list[pl.DataFrame] = []
        if include_national:
            for off in offenses:
                frames.append(
                    normalize.property_to_frame(
                        self.client.property_national(off, from_, to),
                        level="national",
                        area="US",
                        offense=off,
                    )
                )
        for st in states:
            for off in offenses:
                frames.append(
                    normalize.property_to_frame(
                        self.client.property_state(st, off, from_, to),
                        level="state",
                        area=st,
                        offense=off,
                    )
                )
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.PROPERTY_SCHEMA)
        self._write("property", frame)
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
