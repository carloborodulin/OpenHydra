"""Pure functions that flatten CDE response models into tidy long-format frames.

Kept free of any I/O so they can be unit-tested against the saved sample
fixtures with no network.
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

import polars as pl
from cdeclient.models import (
    Agency,
    ArrestTotalsResponse,
    ChartResponse,
    HateCrimeResponse,
    NibrsResponse,
    PropertyResponse,
    ShrResponse,
    SummarizedResponse,
)


class _HasBreakdowns(Protocol):
    @property
    def breakdowns(self) -> dict[str, object]: ...


SUMMARIZED_SCHEMA: dict[str, pl.DataType] = {
    "level": pl.String(),
    "area": pl.String(),
    "offense": pl.String(),
    "series": pl.String(),  # offenses | clearances
    "measure": pl.String(),  # rate | actual
    "period": pl.Date(),
    "value": pl.Float64(),
}

AGENCIES_SCHEMA: dict[str, pl.DataType] = {
    "ori": pl.String(),
    "agency_name": pl.String(),
    "agency_type": pl.String(),
    "county": pl.String(),
    "state_abbr": pl.String(),
    "state_name": pl.String(),
    "latitude": pl.Float64(),
    "longitude": pl.Float64(),
    "is_nibrs": pl.Boolean(),
    "nibrs_start_date": pl.String(),
}

ARRESTS_SCHEMA: dict[str, pl.DataType] = {
    "level": pl.String(),
    "area": pl.String(),
    "offense": pl.String(),
    "category": pl.String(),
    "label": pl.String(),
    "value": pl.Float64(),
}

HATE_CRIME_SCHEMA: dict[str, pl.DataType] = {
    "level": pl.String(),
    "area": pl.String(),
    "category": pl.String(),  # dimension (e.g. bias_category, offender_race, victim_type)
    "label": pl.String(),  # e.g. Religion, Anti-Jewish, White
    "value": pl.Float64(),  # incident/offense count
}

SHR_SCHEMA: dict[str, pl.DataType] = {
    "level": pl.String(),
    "area": pl.String(),
    "category": pl.String(),  # section_dimension (e.g. victim_age, offense_weapons)
    "label": pl.String(),
    "value": pl.Float64(),
}

PROPERTY_SCHEMA: dict[str, pl.DataType] = {
    "level": pl.String(),
    "area": pl.String(),
    "offense": pl.String(),  # NB | NL | NMVT | NROB
    "category": pl.String(),  # dimension (stolen_value, recovered_value, location_counts, …)
    "label": pl.String(),
    "value": pl.Float64(),
}

NIBRS_SCHEMA: dict[str, pl.DataType] = {
    "level": pl.String(),
    "area": pl.String(),
    "offense": pl.String(),  # NIBRS offense code (e.g. 13A)
    "category": pl.String(),  # section_dimension (victim_age, offense_weapons, …)
    "label": pl.String(),
    "value": pl.Float64(),
}

PE_SCHEMA: dict[str, pl.DataType] = {
    "level": pl.String(),
    "area": pl.String(),
    "section": pl.String(),  # rate | actual
    "metric": pl.String(),
    "year": pl.Int32(),
    "value": pl.Float64(),
}


def _month_to_date(period: str) -> date:
    """'MM-YYYY' -> first of that month."""
    mm, yyyy = period.split("-")
    return date(int(yyyy), int(mm), 1)


def _series_kind(series_name: str) -> str:
    name = series_name.lower()
    if "clearance" in name:
        return "clearances"
    if "offense" in name:
        return "offenses"
    return "other"


def summarized_to_frame(
    resp: SummarizedResponse, *, level: str, area: str, offense: str
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for measure, ts in (("rate", resp.offenses.rates), ("actual", resp.offenses.actuals)):
        for series_name, points in ts.items():
            # State/agency queries also return a "United States ..." benchmark
            # series for comparison; it would otherwise be mis-tagged with the
            # queried area and collide with the area's own series. Keep only the
            # area's own series (the national query's own series IS "United
            # States ...", so it's preserved).
            if level != "national" and series_name.startswith("United States"):
                continue
            kind = _series_kind(series_name)
            for period, value in points.items():
                rows.append(
                    {
                        "level": level,
                        "area": area,
                        "offense": offense,
                        "series": kind,
                        "measure": measure,
                        "period": _month_to_date(period),
                        "value": None if value is None else float(value),
                    }
                )
    return pl.DataFrame(rows, schema=SUMMARIZED_SCHEMA)


def agencies_to_frame(by_county: dict[str, list[Agency]]) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for county, agencies in by_county.items():
        for a in agencies:
            rows.append(
                {
                    "ori": a.ori,
                    "agency_name": a.agency_name,
                    "agency_type": a.agency_type_name,
                    "county": a.counties or county,
                    "state_abbr": a.state_abbr,
                    "state_name": a.state_name,
                    "latitude": a.latitude,
                    "longitude": a.longitude,
                    "is_nibrs": a.is_nibrs,
                    "nibrs_start_date": a.nibrs_start_date,
                }
            )
    return pl.DataFrame(rows, schema=AGENCIES_SCHEMA)


def arrests_to_frame(
    resp: ArrestTotalsResponse, *, level: str, area: str, offense: str
) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for category, mapping in resp.breakdowns.items():
        if not isinstance(mapping, dict):
            continue
        for label, value in mapping.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                rows.append(
                    {
                        "level": level,
                        "area": area,
                        "offense": offense,
                        "category": category,
                        "label": str(label),
                        "value": float(value),
                    }
                )
    return pl.DataFrame(rows, schema=ARRESTS_SCHEMA)


def _breakdowns_to_frame(
    resp: _HasBreakdowns,
    schema: dict[str, pl.DataType],
    *,
    level: str,
    area: str,
    extra: dict[str, object] | None = None,
) -> pl.DataFrame:
    """Flatten any ``{dimension: {label: count}}`` breakdowns into tidy long rows
    (level, area, [extra columns], category, label, value). Shared by hate crime,
    SHR, and expanded property (which passes ``extra={"offense": ...}``)."""
    base = {"level": level, "area": area, **(extra or {})}
    rows: list[dict[str, object]] = []
    for category, mapping in resp.breakdowns.items():
        if not isinstance(mapping, dict):
            continue
        for label, value in mapping.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                rows.append(
                    {**base, "category": category, "label": str(label), "value": float(value)}
                )
    return pl.DataFrame(rows, schema=schema)


def hate_crime_to_frame(resp: HateCrimeResponse, *, level: str, area: str) -> pl.DataFrame:
    """Flatten bias_section + incident_section dimensions to tidy long rows
    (same (category, label, value) shape as arrests, minus the offense column)."""
    return _breakdowns_to_frame(resp, HATE_CRIME_SCHEMA, level=level, area=area)


def shr_to_frame(resp: ShrResponse, *, level: str, area: str) -> pl.DataFrame:
    """Flatten the SHR victim/offense/offender dimensions to tidy long rows; the
    category is ``<section>_<dimension>`` (e.g. victim_age, offense_weapons)."""
    return _breakdowns_to_frame(resp, SHR_SCHEMA, level=level, area=area)


def property_to_frame(
    resp: PropertyResponse, *, level: str, area: str, offense: str
) -> pl.DataFrame:
    """Flatten expanded-property value/count dimensions to tidy long rows, keyed
    on the property offense (NB/NL/NMVT/NROB)."""
    return _breakdowns_to_frame(
        resp, PROPERTY_SCHEMA, level=level, area=area, extra={"offense": offense}
    )


def nibrs_to_frame(resp: NibrsResponse, *, level: str, area: str, offense: str) -> pl.DataFrame:
    """Flatten NIBRS victim/offense/offender dimensions to tidy long rows, keyed
    on the NIBRS offense code; category is ``<section>_<dimension>``."""
    return _breakdowns_to_frame(
        resp, NIBRS_SCHEMA, level=level, area=area, extra={"offense": offense}
    )


def pe_to_frame(resp: ChartResponse, *, level: str, area: str) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    for section, ts in (("rate", resp.rates), ("actual", resp.actuals)):
        for metric, points in ts.items():
            for year, value in points.items():
                rows.append(
                    {
                        "level": level,
                        "area": area,
                        "section": section,
                        "metric": metric,
                        "year": int(year),
                        "value": None if value is None else float(value),
                    }
                )
    return pl.DataFrame(rows, schema=PE_SCHEMA)
