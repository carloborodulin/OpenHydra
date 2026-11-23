"""Orchestrates CDE API calls and lands tidy Parquet in a staging directory.

Each upstream request produces one *part* file under ``<out>/_parts/<domain>/``.
A domain file (for example ``summarized.parquet``) is written only after every
part of the domain succeeds, so a failure never leaves half a domain. A rerun
in the same directory reuses the parts that exist, so a long run can resume.
The run manifest (see :mod:`snapshot`) records the outcome of each request.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path

import polars as pl
from cdeclient import CdeClient, CdeError
from cdeclient.constants import (
    ARREST_OFFENSE_CODES,
    ARREST_OFFENSES,
    EXPANDED_PROPERTY_OFFENSES,
    LESDC_CHART_TYPES,
    NIBRS_ESTIMATION_OFFENSES,
    NIBRS_ESTIMATION_REGIONS,
    NIBRS_OFFENSES,
    Offense,
    arrest_components,
)
from cdeclient.dates import to_month, year_of

from . import normalize
from .snapshot import RunLog, write_parquet_atomic

ALL_OFFENSES: list[str] = [o.value for o in Offense]
# All 48 arrest offense slugs (the full `arrest_offense` taxonomy).
ALL_ARREST_OFFENSES: list[str] = list(ARREST_OFFENSES)
# The default arrest pull: the all-offense total plus the 8 Part I offenses.
DEFAULT_ARREST_OFFENSES: list[str] = ["all", *ARREST_OFFENSE_CODES]
# LESDC has data for these years only (national, year-keyed).
LESDC_YEARS: list[str] = ["2022", "2023"]
# Use-of-Force collection years (national, year-keyed).
UOF_YEARS: list[str] = ["2019", "2020", "2021", "2022", "2023"]
# NIBRS estimations latest data year (lookup reports 2021 + 2022).
NIBRS_ESTIMATION_YEAR: str = "2022"

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def year_windows(from_: str, to: str) -> list[tuple[int, str, str]]:
    """Split a month window into calendar-year windows: (year, MM-YYYY, MM-YYYY).

    The first and the last year keep the months of the original window.
    """
    start, end = to_month(from_), to_month(to)
    y0, y1 = int(year_of(start)), int(year_of(end))
    out = []
    for y in range(y0, y1 + 1):
        out.append((y, start if y == y0 else f"01-{y}", end if y == y1 else f"12-{y}"))
    return out


class DomainFailed(RuntimeError):
    """A request of a domain failed, so the domain is not written."""

    def __init__(self, domain: str, key: str, error: CdeError) -> None:
        super().__init__(f"{domain}: {key}: {type(error).__name__}: {error}")
        self.domain = domain
        self.key = key
        self.error = error


class Extractor:
    """Pulls CDE data via :class:`cdeclient.CdeClient` and writes Parquet.

    Args:
        client: the CDE client (use the BULK policy for a full pull).
        out_dir: the staging directory of this run.
        run: the run manifest. Without it, nothing is recorded.
        per_hour: the maximum number of upstream requests per hour, or 0 for
            no limit. The default extract uses about 70% of the key quota.
    """

    def __init__(
        self,
        client: CdeClient,
        out_dir: Path,
        *,
        run: RunLog | None = None,
        per_hour: float = 0.0,
        sleep: Callable[[float], object] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.run = run
        self._interval = 3600.0 / per_hour if per_hour > 0 else 0.0
        self._sleep = sleep
        self._clock = clock
        self._last: float | None = None
        self.requests = 0

    # -- plumbing ------------------------------------------------------------
    def _pace(self) -> None:
        if self._interval and self._last is not None:
            wait = self._last + self._interval - self._clock()
            if wait > 0:
                self._sleep(wait)
        self._last = self._clock()

    def _part(
        self,
        domain: str,
        key: str,
        produce: Callable[[], pl.DataFrame],
        *,
        tolerant: bool = False,
    ) -> pl.DataFrame | None:
        """Return the frame of one request, from its part file or from upstream."""
        path = self.out_dir / "_parts" / domain / f"{_UNSAFE.sub('_', key)}.parquet"
        if path.is_file():
            frame = pl.read_parquet(path)
            if self.run:
                self.run.record(domain, key, "ok" if frame.height else "empty")
            return frame
        self._pace()
        self.requests += 1
        try:
            frame = produce()
        except CdeError as exc:
            if self.run:
                self.run.record(domain, key, "error", f"{type(exc).__name__}: {exc}")
            if tolerant:
                return None
            raise DomainFailed(domain, key, exc) from None
        path.parent.mkdir(parents=True, exist_ok=True)
        write_parquet_atomic(frame, path)
        if self.run:
            self.run.record(domain, key, "ok" if frame.height else "empty")
        return frame

    def _write(self, name: str, frames: list[pl.DataFrame], schema: dict[str, pl.DataType]) -> Path:
        frame = pl.concat(frames) if frames else pl.DataFrame(schema=schema)
        path = self.out_dir / f"{name}.parquet"
        write_parquet_atomic(frame, path)
        return path

    @staticmethod
    def _areas(states: list[str], include_national: bool) -> list[tuple[str, str]]:
        areas = [("national", "US")] if include_national else []
        return areas + [("state", st) for st in states]

    # -- single-request producers --------------------------------------------------
    def _agencies(self, state: str) -> pl.DataFrame:
        return normalize.agencies_to_frame(self.client.agencies_by_state(state))

    def _lesdc(self, year: str, chart_type: str) -> pl.DataFrame:
        resp = self.client.lesdc(chart_type, year)
        return normalize.lesdc_to_frame(resp, year=int(year), chart_type=chart_type)

    def _uof_participation(self, year: str) -> pl.DataFrame:
        return normalize.uof_participation_to_frame([self.client.uof_participation_national(year)])

    def _uof_questions(self, year: str) -> pl.DataFrame:
        return normalize.uof_questions_to_frame(self.client.uof_questions(year), year=int(year))

    # -- domains ---------------------------------------------------------------
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
        for level, area in self._areas(states, include_national):
            for off in offenses:

                def produce(level: str = level, area: str = area, off: str = off) -> pl.DataFrame:
                    resp = (
                        self.client.summarized_national(off, from_, to)
                        if level == "national"
                        else self.client.summarized_state(area, off, from_, to)
                    )
                    return normalize.summarized_to_frame(resp, level=level, area=area, offense=off)

                part = self._part("summarized", f"{area}:{off}", produce)
                assert part is not None
                frames.append(part)
        path = self._write("summarized", frames, normalize.SUMMARIZED_SCHEMA)
        return pl.read_parquet(path)

    def pull_agencies(self, states: list[str]) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        for st in states:
            part = self._part("agencies", st, partial(self._agencies, st))
            assert part is not None
            frames.append(part)
        path = self._write("agencies", frames, normalize.AGENCIES_SCHEMA)
        return pl.read_parquet(path)

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
        # offense slugs. Each requested slug resolves to one or more codes: a
        # rollup (violent-crime, property-crime) gives its component codes, and
        # dbt adds the rollup back up. Each unique code is fetched once per area
        # and written once, keyed by its canonical arrest slug.
        codes: list[str] = list(
            dict.fromkeys(code for off in offenses for code in arrest_components(off))
        )
        window = (to_month(from_), to_month(to))
        frames: list[pl.DataFrame] = []
        for level, area in self._areas(states, include_national):
            for code in codes:

                def produce(level: str = level, area: str = area, code: str = code) -> pl.DataFrame:
                    resp = (
                        self.client.arrests_national(code, from_=from_, to=to)
                        if level == "national"
                        else self.client.arrests_state(area, code, from_=from_, to=to)
                    )
                    return normalize.arrests_to_frame(
                        resp,  # type: ignore[arg-type]
                        level=level,
                        area=area,
                        code=code,
                        window_from=window[0],
                        window_to=window[1],
                    )

                part = self._part("arrests", f"{area}:{code}", produce)
                assert part is not None
                frames.append(part)
        path = self._write("arrests", frames, normalize.ARRESTS_SCHEMA)
        return pl.read_parquet(path)

    def _breakdown_domain(
        self,
        domain: str,
        name: str,
        schema: dict[str, pl.DataType],
        states: list[str],
        include_national: bool,
        offenses: list[str] | None,
        produce_for: Callable[[str, str, str | None], pl.DataFrame],
    ) -> pl.DataFrame:
        frames: list[pl.DataFrame] = []
        offs: list[str | None] = list(offenses) if offenses else [None]
        for level, area in self._areas(states, include_national):
            for off in offs:
                key = f"{area}:{off}" if off else area
                part = self._part(domain, key, partial(produce_for, level, area, off))
                assert part is not None
                frames.append(part)
        path = self._write(name, frames, schema)
        return pl.read_parquet(path)

    def pull_hate_crime(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        def produce(level: str, area: str, _: str | None) -> pl.DataFrame:
            resp = (
                self.client.hate_crime_national(from_, to)
                if level == "national"
                else self.client.hate_crime_state(area, from_, to)
            )
            return normalize.hate_crime_to_frame(resp, level=level, area=area)

        return self._breakdown_domain(
            "hate-crime",
            "hate_crime",
            normalize.HATE_CRIME_SCHEMA,
            states,
            include_national,
            None,
            produce,
        )

    def pull_shr(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        def produce(level: str, area: str, _: str | None) -> pl.DataFrame:
            resp = (
                self.client.shr_national(from_, to)
                if level == "national"
                else self.client.shr_state(area, from_, to)
            )
            return normalize.shr_to_frame(resp, level=level, area=area)

        return self._breakdown_domain(
            "shr", "shr", normalize.SHR_SCHEMA, states, include_national, None, produce
        )

    def pull_property(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        """Expanded property values, one request per area, offense and year.

        The API returns totals for the request window. One window per calendar
        year gives annual values, so a per-resident figure can use the
        population of the same year.
        """
        frames: list[pl.DataFrame] = []
        for level, area in self._areas(states, include_national):
            for off in EXPANDED_PROPERTY_OFFENSES:
                for year, start, end in year_windows(from_, to):
                    part = self._part(
                        "property",
                        f"{area}:{off}:{year}",
                        partial(self._property, level, area, off, year, start, end),
                    )
                    assert part is not None
                    frames.append(part)
        path = self._write("property", frames, normalize.PROPERTY_SCHEMA)
        return pl.read_parquet(path)

    def _property(
        self, level: str, area: str, off: str, year: int, start: str, end: str
    ) -> pl.DataFrame:
        resp = (
            self.client.property_national(off, start, end)
            if level == "national"
            else self.client.property_state(area, off, start, end)
        )
        return normalize.property_to_frame(resp, level=level, area=area, offense=off, year=year)

    def pull_nibrs(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        def produce(level: str, area: str, off: str | None) -> pl.DataFrame:
            assert off is not None
            resp = (
                self.client.nibrs_national(off, from_, to)
                if level == "national"
                else self.client.nibrs_state(area, off, from_, to)
            )
            return normalize.nibrs_to_frame(resp, level=level, area=area, offense=off)

        return self._breakdown_domain(
            "nibrs",
            "nibrs",
            normalize.NIBRS_SCHEMA,
            states,
            include_national,
            list(NIBRS_OFFENSES),  # curated subset of the 72 codes
            produce,
        )

    def pull_lesdc(
        self, years: list[str] | None = None, chart_types: list[str] | None = None
    ) -> pl.DataFrame:
        # LESDC is national-only and keyed by year + chart type (no state/agency).
        frames: list[pl.DataFrame] = []
        for yr in years or LESDC_YEARS:
            for ct in chart_types or list(LESDC_CHART_TYPES):
                part = self._part("lesdc", f"{yr}:{ct}", partial(self._lesdc, yr, ct))
                assert part is not None
                frames.append(part)
        path = self._write("lesdc", frames, normalize.LESDC_SCHEMA)
        return pl.read_parquet(path)

    def pull_nibrs_estimation(self, year: str = NIBRS_ESTIMATION_YEAR) -> tuple[pl.DataFrame, int]:
        """National + the four regions, for a curated offense set.

        The modeled-estimation endpoint is slow and some combinations fail, so
        this domain tolerates a failed request: it records the error and goes on.
        Returns the frame and the number of failed requests. The promote step
        refuses a result that covers less than the current release.
        """
        geos: list[tuple[str, str, str | None]] = [("national", "US", None)]
        geos += [("region", name, code) for code, name in NIBRS_ESTIMATION_REGIONS.items()]
        frames: list[pl.DataFrame] = []
        failed = 0
        for off in NIBRS_ESTIMATION_OFFENSES:
            for level, area, code in geos:

                def produce(
                    level: str = level, area: str = area, code: str | None = code, off: str = off
                ) -> pl.DataFrame:
                    resp = (
                        self.client.nibrs_estimation_national(off, year)
                        if code is None
                        else self.client.nibrs_estimation_region(code, off, year)
                    )
                    return normalize.nibrs_estimation_to_frame(
                        resp, level=level, area=area, offense=off
                    )

                part = self._part("nibrs-estimation", f"{area}:{off}", produce, tolerant=True)
                if part is None:
                    failed += 1
                else:
                    frames.append(part)
        path = self._write("nibrs_estimation", frames, normalize.NIBRS_ESTIMATION_SCHEMA)
        return pl.read_parquet(path), failed

    def pull_uof(self, years: list[str] | None = None) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Use of Force (national, year-keyed): participation and questions.

        Both files are written only after every request of both succeeds. A 404
        on the participation route is an upstream contract change (seen at the
        2026-11-22 audit); the domain then fails and the release keeps its data.
        """
        years = years or UOF_YEARS
        part_frames: list[pl.DataFrame] = []
        q_frames: list[pl.DataFrame] = []
        for yr in years:
            p = self._part("uof", f"participation:{yr}", partial(self._uof_participation, yr))
            q = self._part("uof", f"questions:{yr}", partial(self._uof_questions, yr))
            assert p is not None and q is not None
            part_frames.append(p)
            q_frames.append(q)
        p_path = self._write("uof_participation", part_frames, normalize.UOF_PARTICIPATION_SCHEMA)
        q_path = self._write("uof_questions", q_frames, normalize.UOF_QUESTIONS_SCHEMA)
        return pl.read_parquet(p_path), pl.read_parquet(q_path)

    def pull_pe(
        self, states: list[str], from_: str, to: str, *, include_national: bool = True
    ) -> pl.DataFrame:
        fy, ty = year_of(from_), year_of(to)

        def produce(level: str, area: str, _: str | None) -> pl.DataFrame:
            resp = (
                self.client.police_employment_national(fy, ty)
                if level == "national"
                else self.client.police_employment_state(area, fy, ty)
            )
            return normalize.pe_to_frame(resp, level=level, area=area)

        return self._breakdown_domain(
            "pe", "pe", normalize.PE_SCHEMA, states, include_national, None, produce
        )
