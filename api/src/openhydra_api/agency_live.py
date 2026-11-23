"""Live agency-level drill-down: fetch from the CDE API on demand and shape it
into the same row models the warehouse marts serve.

Per-agency data for ~19,619 agencies can't be pre-materialized into the static
seed warehouse, so these helpers call the FBI gateway live (via ``cdeclient``)
and normalize the responses into the existing ``OffenseMonthly`` / ``ArrestRow``
/ ``PoliceEmploymentRow`` shapes — reproducing the dbt mart logic (notably the
clearance-ratio pivot in ``fct_offenses_monthly.sql``) in Python so the frontend
reuses its types and chart components unchanged.

An in-process LRU cache with single flight fronts the live calls, and
``live_guard`` limits the upstream work (see ``LiveCache`` and ``fetch``).
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from cdeclient.models import ArrestTotalsResponse, ChartResponse, SummarizedResponse

from . import obs
from .live_guard import LiveLimitError, guard


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


# -- in-process cache with single flight ------------------------------------
@dataclass
class _Flight:
    """One upstream fetch that other requests for the same key can wait on."""

    done: threading.Event = field(default_factory=threading.Event)
    rows: list[dict[str, Any]] | None = None
    error: BaseException | None = None


class LiveCache:
    """A thread-safe LRU cache of unfiltered upstream rows.

    - A non-empty result stays for ``ttl`` seconds. A valid empty result (the
      agency has no data) stays for ``empty_ttl`` seconds, so repeat requests
      for it do not spend quota.
    - An upstream error is never stored.
    - Concurrent misses for one key make one upstream call (single flight).
      The other requests wait for it and get the same result or error.
    - Each caller gets its own copy of the rows.
    """

    def __init__(
        self,
        *,
        max_entries: int = 512,
        ttl: float = 3600.0,
        empty_ttl: float = 300.0,
        wait_timeout: float = 20.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_entries = max_entries
        self.ttl = ttl
        self.empty_ttl = empty_ttl
        self.wait_timeout = wait_timeout
        self._clock = clock
        self._lock = threading.Lock()
        self._data: OrderedDict[str, tuple[float, list[dict[str, Any]]]] = OrderedDict()
        self._inflight: dict[str, _Flight] = {}

    def __len__(self) -> int:
        return len(self._data)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def get(self, key: str, produce: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
        with self._lock:
            hit = self._data.get(key)
            if hit is not None and self._clock() < hit[0]:
                self._data.move_to_end(key)
                obs.note(cache="hit")
                return _copy(hit[1])
            flight = self._inflight.get(key)
            leader = flight is None
            if flight is None:
                flight = _Flight()
                self._inflight[key] = flight

        if not leader:
            obs.note(cache="coalesced")
            if not flight.done.wait(self.wait_timeout):
                raise LiveLimitError(
                    503, "live_busy", "Live agency data is busy. Try again in a moment.", 5
                )
            if flight.error is not None:
                raise flight.error
            return _copy(flight.rows or [])

        obs.note(cache="miss")
        try:
            rows = produce()
            obs.note(upstream="2xx")
            with self._lock:
                expires = self._clock() + (self.ttl if rows else self.empty_ttl)
                self._data[key] = (expires, rows)
                self._data.move_to_end(key)
                while len(self._data) > self.max_entries:
                    self._data.popitem(last=False)
            flight.rows = rows
            return _copy(rows)
        except BaseException as exc:
            flight.error = exc
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)
            flight.done.set()


def _copy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


cache = LiveCache()


def cache_key(kind: str, *parts: str) -> str:
    """A canonical key. Callers pass validated, upper-case ORIs and offense codes."""
    return ":".join((kind, *parts))


def fetch(key: str, produce: Callable[[], list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Get rows from the cache, or charge the live budget and call ``produce``.

    ``produce`` must return the unfiltered rows. Filter by category after.
    """

    def guarded() -> list[dict[str, Any]]:
        guard.admit(obs.client_id())
        with guard.upstream_slot():
            return produce()

    return cache.get(key, guarded)


def filter_category(rows: list[dict[str, Any]], category: str | None) -> list[dict[str, Any]]:
    return rows if category is None else [r for r in rows if r["category"] == category]


def clear_cache() -> None:
    """Drop all cached entries (used by tests)."""
    cache.clear()
