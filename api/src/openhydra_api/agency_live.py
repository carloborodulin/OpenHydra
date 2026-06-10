"""Live agency-level drill-down: fetch from the CDE API on demand and shape it
into the same row models the warehouse marts serve.

Per-agency data for ~19,619 agencies can't be pre-materialized into the static
seed warehouse, so these helpers call the FBI gateway live (via ``cdeclient``)
and normalize the responses into the existing ``OffenseMonthly`` / ``ArrestRow``
/ ``PoliceEmploymentRow`` shapes — reproducing the dbt mart logic (notably the
clearance-ratio pivot in ``fct_offenses_monthly.sql``) in Python so the frontend
reuses its types and chart components unchanged.

A tiny in-process TTL cache fronts the live calls. It caches only successful,
non-empty results, so a transient gateway 503 (which surfaces as ``[]``) never
sticks — the next request retries.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from typing import Any

from cdeclient.models import ArrestTotalsResponse, ChartResponse, SummarizedResponse


def _month_to_date(period: str) -> date:
    """'MM-YYYY' -> first of that month (matches OffenseMonthly.period)."""
    mm, yyyy = period.split("-")
    return date(int(yyyy), int(mm), 1)


def _series_kind(series_name: str) -> str:
    # Same rule as openhydra_etl.normalize._series_kind.
    name = series_name.lower()
    if "clearance" in name:
        return "clearances"
    if "offense" in name:
        return "offenses"
    return "other"


def offenses_to_rows(resp: SummarizedResponse) -> list[dict[str, Any]]:
    """Pivot long series/measure points into one row per month.

    Mirrors ``warehouse/dbt/models/marts/fct_offenses_monthly.sql``:
    ``clearance_ratio = clearances_actual / nullif(offenses_actual, 0)``.
    """
    # An agency query returns the agency's own series PLUS state + "United
    # States" benchmark series for comparison — but only in `rates`; `actuals`
    # holds the agency's own series alone. So treat the actuals keys as the set
    # of "own" series and drop any rates series not in it, otherwise the pivot
    # would mix the agency's rate with the state/national benchmark rates.
    own_series = set(resp.offenses.actuals)
    acc: dict[date, dict[str, float | None]] = {}
    for measure, ts in (("rate", resp.offenses.rates), ("actual", resp.offenses.actuals)):
        for series_name, points in ts.items():
            if measure == "rate" and series_name not in own_series:
                continue
            kind = _series_kind(series_name)
            if kind == "other":
                continue
            for period, value in points.items():
                cell = acc.setdefault(_month_to_date(period), {})
                cell[f"{kind}_{measure}"] = None if value is None else float(value)

    rows: list[dict[str, Any]] = []
    for d in sorted(acc):
        cell = acc[d]
        off_actual = cell.get("offenses_actual")
        clr_actual = cell.get("clearances_actual")
        ratio = (
            clr_actual / off_actual
            if clr_actual is not None and off_actual is not None and off_actual != 0
            else None
        )
        rows.append(
            {
                "period": d,
                "offenses_rate": cell.get("offenses_rate"),
                "offenses_actual": off_actual,
                "clearances_rate": cell.get("clearances_rate"),
                "clearances_actual": clr_actual,
                "clearance_ratio": ratio,
            }
        )
    return rows


def breakdowns_to_rows(
    breakdowns: dict[str, Any], category: str | None = None
) -> list[dict[str, Any]]:
    """Flatten {dimension: {label: count}} breakdowns to ArrestRow shape, optionally
    restricted to one dimension. Shared by arrests and hate crime; mirrors the
    API's ``order by category, value desc``."""
    rows: list[dict[str, Any]] = []
    for cat, mapping in breakdowns.items():
        if category and cat != category:
            continue
        if not isinstance(mapping, dict):
            continue
        for label, value in mapping.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                rows.append({"category": cat, "label": str(label), "value": float(value)})
    rows.sort(key=lambda r: (r["category"], -(r["value"] or 0.0)))
    return rows


def arrests_to_rows(
    resp: ArrestTotalsResponse, category: str | None = None
) -> list[dict[str, Any]]:
    """Flatten demographic breakdowns to ArrestRow shape (optionally one category).

    Mirrors openhydra_etl.normalize.arrests_to_frame.
    """
    return breakdowns_to_rows(resp.breakdowns, category)


def pe_to_rows(resp: ChartResponse) -> list[dict[str, Any]]:
    """Flatten /pe rates+actuals to PoliceEmploymentRow shape (order by metric, year)."""
    rows: list[dict[str, Any]] = []
    for section, ts in (("rate", resp.rates), ("actual", resp.actuals)):
        for metric, points in ts.items():
            for year, value in points.items():
                rows.append(
                    {
                        "section": section,
                        "metric": metric,
                        "year": int(year),
                        "value": None if value is None else float(value),
                    }
                )
    rows.sort(key=lambda r: (r["metric"], r["year"]))
    return rows


# -- tiny in-process TTL cache ---------------------------------------------
_TTL_SECONDS = 3600.0
_MAX_ENTRIES = 512
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def cache_key(*parts: str | None) -> str:
    return "|".join("" if p is None else p for p in parts)


def cached(key: str, produce: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Return cached rows, else call ``produce`` and cache only non-empty results."""
    now = time.monotonic()
    hit = _cache.get(key)
    if hit is not None and now - hit[0] < _TTL_SECONDS:
        return hit[1]
    rows = produce()
    if rows:  # never cache empties (transient errors / no-data)
        if len(_cache) >= _MAX_ENTRIES:
            del _cache[min(_cache, key=lambda k: _cache[k][0])]  # evict oldest
        _cache[key] = (now, rows)
    return rows


def clear_cache() -> None:
    """Drop all cached entries (used by tests)."""
    _cache.clear()
