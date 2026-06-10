"""Orchestrates CDE API calls and lands tidy Parquet under data/raw/."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import httpx
import polars as pl
from cdeclient import CdeClient, CdeError
from cdeclient.constants import (
    ARREST_OFFENSES,
    EXPANDED_PROPERTY_OFFENSES,
    LESDC_CHART_TYPES,
    NIBRS_ESTIMATION_OFFENSES,
    NIBRS_ESTIMATION_REGIONS,
    NIBRS_OFFENSES,
    Offense,
    arrest_code,
)

from . import normalize
from .config import RAW_DIR

ALL_OFFENSES: list[str] = [o.value for o in Offense]
# All 48 arrest offense slugs (the full `arrest_offense` taxonomy).
ALL_ARREST_OFFENSES: list[str] = list(ARREST_OFFENSES)
# LESDC has data for these years only (national, year-keyed).
LESDC_YEARS: list[str] = ["2022", "2023"]
# Use-of-Force collection years (national, year-keyed).
UOF_YEARS: list[str] = ["2019", "2020", "2021", "2022", "2023"]
# NIBRS estimations latest data year (lookup reports 2021 + 2022).
NIBRS_ESTIMATION_YEAR: str = "2022"


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

    def pull_nibrs(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        offenses = list(NIBRS_OFFENSES)  # curated subset of the 72 codes
        frames: list[pl.DataFrame] = []
        if include_national:
            for off in offenses:
                frames.append(
                    normalize.nibrs_to_frame(
                        self.client.nibrs_national(off, from_, to),
                        level="national",
                        area="US",
                        offense=off,
                    )
                )
        for st in states:
            for off in offenses:
                frames.append(
                    normalize.nibrs_to_frame(
                        self.client.nibrs_state(st, off, from_, to),
                        level="state",
                        area=st,
                        offense=off,
                    )
                )
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.NIBRS_SCHEMA)
        self._write("nibrs", frame)
        return frame

    def pull_lesdc(
        self, years: list[str] | None = None, chart_types: list[str] | None = None
    ) -> pl.DataFrame:
        # LESDC is national-only and keyed by year + chart type (no state/agency).
        years = years or LESDC_YEARS
        charts = chart_types or list(LESDC_CHART_TYPES)
        frames: list[pl.DataFrame] = []
        for yr in years:
            for ct in charts:
                resp = self.client.lesdc(ct, yr)
                frames.append(normalize.lesdc_to_frame(resp, year=int(yr), chart_type=ct))
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=normalize.LESDC_SCHEMA)
        self._write("lesdc", frame)
        return frame

    def pull_nibrs_estimation(self, year: str = NIBRS_ESTIMATION_YEAR) -> pl.DataFrame:
        # National + the four regions, for a curated offense set (no state/agency-
        # type/size facets). Estimates only; confidence bounds are dropped. The
        # modeled-estimation endpoint is slow and occasionally times out, so skip
        # (and report) any combo that fails rather than aborting the whole pull.
        # geo = (level, area, region_code|None)
        geos: list[tuple[str, str, str | None]] = [("national", "US", None)]
        geos += [("region", name, code) for code, name in NIBRS_ESTIMATION_REGIONS.items()]
        frames: list[pl.DataFrame] = []
        skipped: list[str] = []
        for off in NIBRS_ESTIMATION_OFFENSES:
            for level, area, code in geos:
                try:
                    resp = (
                        self.client.nibrs_estimation_national(off, year)
                        if code is None
                        else self.client.nibrs_estimation_region(code, off, year)
                    )
                except (CdeError, httpx.HTTPError):
                    skipped.append(f"{area}/{off}")
                    continue
                frames.append(
                    normalize.nibrs_estimation_to_frame(resp, level=level, area=area, offense=off)
                )
        if skipped:
            print(f"  nibrs-estimation: skipped {len(skipped)} combos: {skipped}", file=sys.stderr)
        frame = (
            pl.concat(frames) if frames else pl.DataFrame(schema=normalize.NIBRS_ESTIMATION_SCHEMA)
        )
        self._write("nibrs_estimation", frame)
        return frame

    def pull_uof(self, years: list[str] | None = None) -> tuple[pl.DataFrame, pl.DataFrame]:
        # Use of Force is national + year-keyed: participation summary + report
        # questions. Writes two domains (uof_participation, uof_questions).
        years = years or UOF_YEARS
        part = normalize.uof_participation_to_frame(
            [self.client.uof_participation_national(yr) for yr in years]
        )
        self._write("uof_participation", part)
        q_frames = [
            normalize.uof_questions_to_frame(self.client.uof_questions(yr), year=int(yr))
            for yr in years
        ]
        questions = (
            pl.concat(q_frames) if q_frames else pl.DataFrame(schema=normalize.UOF_QUESTIONS_SCHEMA)
        )
        self._write("uof_questions", questions)
        return part, questions

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
