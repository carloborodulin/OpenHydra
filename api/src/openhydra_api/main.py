"""FastAPI app serving the OpenHydra DuckDB marts as JSON."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import duckdb
from cdeclient import Settings
from cdeclient.constants import (
    ARREST_CODE_TO_SLUG,
    ARREST_OFFENSES,
    ARREST_ROLLUP_NAMES,
    ARREST_ROLLUPS,
    EXPANDED_PROPERTY_OFFENSES,
    NIBRS_OFFENSE_CODES,
    Offense,
    arrest_components,
)
from cdeclient.models import ArrestTotalsResponse
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query
from fastapi import Path as FastPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import agency_live, obs
from .cde import ClientProvider, close_shared_client, get_cde_client
from .config import duckdb_path
from .db import get_conn
from .headers import SecurityAndCacheMiddleware
from .models import (
    AgencyFeature,
    AgencyPoints,
    ArrestAvailability,
    ArrestBreakdownRow,
    ArrestOffense,
    ArrestRow,
    BenchmarkRow,
    Capabilities,
    EstimateRow,
    LesdcRow,
    Meta,
    OffenseMonthly,
    PoliceEmploymentRow,
    PopulationRow,
    PropertyRow,
    PropertyYears,
    Snapshot,
    SnapshotDomain,
    UofParticipationRow,
)

# Request-scoped read-only DuckDB connection (FastAPI Annotated dependency).
Conn = Annotated[duckdb.DuckDBPyConnection, Depends(get_conn)]
# Live CDE client provider for agency drill-down. Routes call it only on a
# cache miss (see cde.py).
Cde = Annotated[ClientProvider, Depends(get_cde_client)]

# Window for live agency calls (mirrors the ETL defaults). Most endpoints take
# MM-YYYY; /pe takes 4-digit years.
LIVE_FROM, LIVE_TO = "01-2015", "12-2024"
LIVE_FROM_YEAR, LIVE_TO_YEAR = "2015", "2024"

# An upstream failure is not an empty result. The handlers in obs.py turn each
# CdeError into a 502, 503 or 504 response, and the cache does not keep it.


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    close_shared_client()


app = FastAPI(
    title="OpenHydra API",
    version="0.1.0",
    description="Read-only access to FBI UCR crime marts (DuckDB).",
    lifespan=lifespan,
)
# The release ID of the warehouse, read once (the file changes only with a deploy).
_release: dict[str, str] = {}


def current_release() -> str | None:
    path = str(duckdb_path())
    if path not in _release:
        try:
            con = duckdb.connect(path, read_only=True)
            try:
                row = con.execute("select release_id from meta_snapshot").fetchone()
            finally:
                con.close()
        except duckdb.Error:
            return None  # not cached: the next request tries again
        if not row:
            return None
        _release[path] = str(row[0])
    return _release[path]


# Security headers and the cache policy wrap the app; the request log (added
# next, so it is outermost) still records 304 answers.
app.add_middleware(SecurityAndCacheMiddleware, release=lambda: current_release())
obs.install(app)

# Every data route is on this router. It is served at /api/v1 (the documented
# version) and at /api (the old paths, kept as aliases with a Deprecation
# header; see headers.py). Both prefixes reach the same handlers.
api = APIRouter()

# The browser talks to this service, never to the upstream API, so the API key
# is never exposed. Open CORS is fine for a public read-only dataset.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _dicts(
    conn: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None
) -> list[dict[str, Any]]:
    cur = conn.execute(sql, params or [])
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


# The tables a valid snapshot must hold, each with at least one row. The
# readiness probe checks them, so a deploy with a missing or empty mart fails
# its health check and the previous deployment keeps serving.
REQUIRED_TABLES: tuple[str, ...] = (
    "meta_snapshot",
    "meta_snapshot_domains",
    "fct_offenses_monthly",
    "dim_agencies",
    "dim_population",
    "fct_arrests",
    "fct_police_employment",
    "fct_hate_crime",
    "fct_shr",
    "fct_property",
    "fct_nibrs",
    "fct_nibrs_estimation",
    "fct_lesdc",
    "fct_uof_participation",
    "fct_uof_questions",
)


def snapshot_problems(conn: duckdb.DuckDBPyConnection) -> list[str]:
    present = {
        r[0] for r in conn.execute("select table_name from information_schema.tables").fetchall()
    }
    problems = []
    for table in REQUIRED_TABLES:
        if table not in present:
            problems.append(f"{table}: missing")
            continue
        row = conn.execute(f"select count(*) from {table}").fetchone()  # noqa: S608 - fixed names
        if not row or row[0] == 0:
            problems.append(f"{table}: no rows")
    return problems


@app.get("/health", response_model=None)
def health(conn: Conn) -> dict[str, Any] | JSONResponse:
    """Readiness: the warehouse opens and every required mart has rows."""
    problems = snapshot_problems(conn)
    if problems:
        return JSONResponse(
            status_code=503,
            content={"status": "invalid_snapshot", "problems": problems},
            headers={"Cache-Control": "no-store"},
        )
    row = conn.execute("select release_id from meta_snapshot").fetchone()
    return {"status": "ok", "release_id": row[0] if row else None}


def _snapshot(conn: duckdb.DuckDBPyConnection) -> Snapshot | None:
    try:
        rows = _dicts(conn, "select * from meta_snapshot limit 1")
        domains = _dicts(conn, "select * from meta_snapshot_domains order by domain")
    except duckdb.CatalogException:
        return None
    if not rows:
        return None
    return Snapshot(**rows[0], domains=[SnapshotDomain(**d) for d in domains])


@api.get("/meta", response_model=Meta)
def meta(conn: Conn) -> Meta:
    offenses = [
        r[0]
        for r in conn.execute(
            "select distinct offense from fct_offenses_monthly order by 1"
        ).fetchall()
    ]
    states = [
        r[0]
        for r in conn.execute(
            "select distinct area from fct_offenses_monthly where level = 'state' order by 1"
        ).fetchall()
    ]
    # The arrest demographic categories actually present in the warehouse
    # (e.g. "Arrestee Race", "Arrestee Sex", "Male Arrests By Age", …) so the
    # frontend can build a category selector instead of hardcoding one.
    arrest_categories = [
        r[0]
        for r in conn.execute("select distinct category from fct_arrests order by 1").fetchall()
    ]
    in_snapshot = {
        r[0]
        for r in conn.execute(
            "select distinct offense from fct_arrests where level = 'national'"
        ).fetchall()
    }
    arrest_offenses = [
        ArrestOffense(
            slug=slug,
            code="derived",
            name=ARREST_ROLLUP_NAMES[slug],
            category="Derived Rollup",
            derived=True,
            in_snapshot=slug in in_snapshot,
        )
        for slug in ARREST_ROLLUPS
    ] + [
        ArrestOffense(
            slug=slug,
            code=info.code,
            name=info.name,
            category=info.category,
            in_snapshot=slug in in_snapshot,
        )
        for slug, info in ARREST_OFFENSES.items()
    ]
    return Meta(
        snapshot=_snapshot(conn),
        capabilities=Capabilities(live_agency=Settings().api_key is not None),
        offenses=offenses,
        states=states,
        levels=["national", "state", "agency"],
        arrest_offenses=arrest_offenses,
        arrest_categories=arrest_categories,
    )


@api.get("/offenses/monthly", response_model=list[OffenseMonthly])
def offenses_monthly(
    conn: Conn,
    offense: str,
    level: str = "national",
    area: str = "US",
) -> list[dict[str, Any]]:
    rows = _dicts(
        conn,
        """
        select period, offenses_rate, offenses_actual,
               clearances_rate, clearances_actual, clearance_ratio,
               ttm_months, ttm_rate, yoy_delta, index_2019
        from fct_offenses_monthly
        where level = ? and area = ? and offense = ?
        order by period
        """,
        [level, area, offense],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="no data for that level/area/offense")
    return rows


@api.get("/offenses/benchmark", response_model=list[BenchmarkRow])
def offenses_benchmark(
    conn: Conn,
    offense: str,
    level: str = "state",
    area: str = "US",
) -> list[dict[str, Any]]:
    """The area's monthly offense rate alongside the national rate for the same
    offense, plus a relative index (area / national * 100; 100 = national average)."""
    rows = _dicts(
        conn,
        """
        select a.period,
               a.offenses_rate as area_rate,
               n.offenses_rate as national_rate,
               a.offenses_rate / nullif(n.offenses_rate, 0) * 100 as relative_index
        from fct_offenses_monthly a
        left join fct_offenses_monthly n
            on n.level = 'national' and n.area = 'US'
           and n.offense = a.offense and n.period = a.period
        where a.level = ? and a.area = ? and a.offense = ?
        order by a.period
        """,
        [level, area, offense],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="no data for that level/area/offense")
    return rows


OriParam = Annotated[
    str,
    FastPath(
        pattern=r"^[A-Za-z]{2}[A-Za-z0-9]{7}$",
        description="A 9-character NCIC ORI, for example NY0303000.",
    ),
]


@api.get("/agencies/points", response_model=AgencyPoints)
def agency_points(conn: Conn, state: str | None = None, v: str | None = None) -> dict[str, Any]:
    """The agency list in a compact column form, for the map and the search.

    Each field is one array, so a key is not repeated about 19,600 times.
    Clients pass ?v=<release ID>; with the current release the answer is
    cached as immutable (see headers.py). Details: /api/agencies/{ori}.
    """
    sql = (
        "select ori, agency_name, county, latitude, longitude, is_nibrs, nibrs_start_year "
        "from dim_agencies"
    )
    params: list[Any] = []
    if state:
        sql += " where state_abbr = ?"
        params.append(state.upper())
    sql += " order by agency_name"
    rows = conn.execute(sql, params).fetchall()
    cols = list(zip(*rows, strict=True)) if rows else [()] * 7
    return {
        "release_id": current_release(),
        "ori": list(cols[0]),
        "name": list(cols[1]),
        "county": list(cols[2]),
        "lat": list(cols[3]),
        "lon": list(cols[4]),
        "nibrs": list(cols[5]),
        "nibrs_start_year": list(cols[6]),
    }


@api.get("/agencies/{ori}", response_model=AgencyFeature)
def agency_detail(ori: OriParam, conn: Conn) -> dict[str, Any]:
    """One agency of the snapshot, by ORI."""
    rows = _dicts(
        conn,
        "select ori, agency_name, agency_type, county, state_abbr, latitude, longitude, "
        "is_nibrs, nibrs_start_year from dim_agencies where ori = ?",
        [ori.upper()],
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Unknown agency ORI {ori.upper()}.")
    return rows[0]


@api.get("/agencies", response_model=list[AgencyFeature])
def agencies(conn: Conn, state: str | None = None) -> list[dict[str, Any]]:
    sql = (
        "select ori, agency_name, agency_type, county, state_abbr, "
        "latitude, longitude, is_nibrs, nibrs_start_year from dim_agencies"
    )
    params: list[Any] = []
    if state:
        sql += " where state_abbr = ?"
        params.append(state.upper())
    sql += " order by agency_name"
    return _dicts(conn, sql, params)


@api.get("/arrests", response_model=list[ArrestBreakdownRow])
def arrests(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    offense: str = "all",
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Arrest breakdowns for one offense. The default offense is "all" (every
    offense together). Each row carries its offense, so totals never mix codes."""
    sql = (
        "select offense, is_derived, category, label, value from fct_arrests "
        "where level = ? and area = ? and offense = ?"
    )
    params: list[Any] = [level, area, offense]
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


@api.get("/arrests/available", response_model=ArrestAvailability)
def arrests_available(conn: Conn, level: str = "national", area: str = "US") -> dict[str, Any]:
    """The arrest offenses that have rows in the snapshot for one scope."""
    rows = conn.execute(
        "select distinct offense from fct_arrests where level = ? and area = ? order by 1",
        [level, area],
    ).fetchall()
    return {"level": level, "area": area, "offenses": [r[0] for r in rows]}


@api.get("/police-employment", response_model=list[PoliceEmploymentRow])
def police_employment(
    conn: Conn,
    level: str = "national",
    area: str = "US",
) -> list[dict[str, Any]]:
    return _dicts(
        conn,
        "select section, metric, year, value from fct_police_employment "
        "where level = ? and area = ? order by metric, year",
        [level, area],
    )


@api.get("/population", response_model=list[PopulationRow])
def population(
    conn: Conn,
    level: str = "national",
    area: str = "US",
) -> list[dict[str, Any]]:
    """U.S. Census population by year — the denominator for per-capita metrics."""
    return _dicts(
        conn,
        "select year, population from dim_population where level = ? and area = ? order by year",
        [level, area],
    )


@api.get("/hate-crime", response_model=list[ArrestRow])
def hate_crime(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    category: str | None = None,
) -> list[dict[str, Any]]:
    # Same tidy (category, label, value) shape as arrests; `category` is the
    # breakdown dimension (bias_category, offender_race, victim_type, …).
    sql = "select category, label, value from fct_hate_crime where level = ? and area = ?"
    params: list[Any] = [level, area]
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


@api.get("/shr", response_model=list[ArrestRow])
def shr(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    category: str | None = None,
) -> list[dict[str, Any]]:
    # Supplementary Homicide Report breakdowns; `category` is section_dimension
    # (victim_age, offense_weapons, offender_race, …).
    sql = "select category, label, value from fct_shr where level = ? and area = ?"
    params: list[Any] = [level, area]
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


@api.get("/property/years", response_model=PropertyYears)
def property_years(
    conn: Conn, level: str = "national", area: str = "US", offense: str = "NB"
) -> dict[str, Any]:
    """The calendar years of expanded property data for one scope and offense."""
    rows = conn.execute(
        "select distinct year from fct_property where level = ? and area = ? and offense = ?",
        [level, area, offense],
    ).fetchall()
    years = sorted(r[0] for r in rows if r[0] is not None)
    return {"years": years, "window_total": any(r[0] is None for r in rows)}


@api.get("/property", response_model=list[PropertyRow])
def expanded_property(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    offense: str | None = None,
    category: str | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    """Expanded property (supplemental) breakdowns for one year.

    `offense` is NB/NL/NMVT/NROB and `category` the value or count dimension.
    Without `year`, the route uses the latest year. When the data has no years
    (an older snapshot), the rows are totals over the whole window (year null).
    """
    sql = "select year, category, label, value from fct_property where level = ? and area = ?"
    params: list[Any] = [level, area]
    if offense:
        sql += " and offense = ?"
        params.append(offense)
    if year is not None:
        sql += " and year = ?"
        params.append(year)
    else:
        sql += (
            " and year is not distinct from (select max(year) from fct_property"
            " where level = ? and area = ?" + (" and offense = ?" if offense else "") + ")"
        )
        params += [level, area] + ([offense] if offense else [])
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


@api.get("/nibrs", response_model=list[ArrestRow])
def nibrs(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    offense: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    # NIBRS incident breakdowns; `offense` is a NIBRS code, `category` the
    # section_dimension (victim_age, offense_weapons, offender_race, …).
    sql = "select category, label, value from fct_nibrs where level = ? and area = ?"
    params: list[Any] = [level, area]
    if offense:
        sql += " and offense = ?"
        params.append(offense)
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


@api.get("/lesdc", response_model=list[LesdcRow])
def lesdc(
    conn: Conn,
    chart_type: str = "manner",
    year: int = 2023,
    section: str | None = None,
) -> list[dict[str, Any]]:
    # LE suicide data collection — national only, by year + chart type, split
    # into S (suicide) / AS (attempted suicide) sections.
    sql = "select section, label, value from fct_lesdc where year = ? and chart_type = ?"
    params: list[Any] = [year, chart_type]
    if section:
        sql += " and section = ?"
        params.append(section)
    sql += " order by section, value desc"
    return _dicts(conn, sql, params)


@api.get("/uof/participation", response_model=list[UofParticipationRow])
def uof_participation(conn: Conn) -> list[dict[str, Any]]:
    # Use-of-Force national reporting participation, one row per year.
    return _dicts(
        conn,
        "select year, participating_agencies, total_agencies, participation_percent "
        "from fct_uof_participation order by year",
    )


@api.get("/uof/questions", response_model=list[ArrestRow])
def uof_questions(
    conn: Conn,
    year: int = 2022,
    category: str | None = None,
) -> list[dict[str, Any]]:
    # Use-of-Force report items; `category` is the quest group (report / contact
    # / force / means).
    sql = "select category, label, value from fct_uof_questions where year = ?"
    params: list[Any] = [year]
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


@api.get("/nibrs-estimation", response_model=list[EstimateRow])
def nibrs_estimation(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    offense: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    # Modeled (estimated) NIBRS counts; level is national|region, `offense` a
    # numeric estimation code, `category` the section_dimension.
    sql = (
        "select category, label, value, lower, upper from fct_nibrs_estimation "
        "where level = ? and area = ?"
    )
    params: list[Any] = [level, area]
    if offense:
        sql += " and offense = ?"
        params.append(offense)
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


# -- agency drill-down (live, proxied from the CDE API) --------------------
# The warehouse only holds national + state rows. Per-agency data for ~19,619
# agencies can't be pre-materialized, so these routes fetch live via cdeclient
# and normalize to the same row shapes the warehouse routes return.
#
# Every input is checked before any upstream call: the ORI must exist in the
# snapshot and each offense must be in the API's own list. The cache key uses
# the canonical values and holds the unfiltered rows; the category filter runs
# after the cache. See agency_live (cache) and live_guard (limits).

CategoryParam = Annotated[str | None, Query(max_length=80)]


def known_ori(ori: OriParam, conn: Conn) -> str:
    """Upper-case the ORI and require it in the agency list of the snapshot."""
    canonical = ori.upper()
    found = conn.execute("select 1 from dim_agencies where ori = ? limit 1", [canonical])
    if found.fetchone() is None:
        raise HTTPException(status_code=404, detail=f"Unknown agency ORI {canonical}.")
    return canonical


Ori = Annotated[str, Depends(known_ori)]


def _arrest_codes_or_422(offense: str | None) -> tuple[str, tuple[str, ...]]:
    """Return the canonical offense slug and the arrest codes whose sum gives it."""
    try:
        codes = arrest_components(offense)
    except ValueError:
        raise HTTPException(
            status_code=422, detail=f"Unknown arrest offense {offense!r}."
        ) from None
    if offense in ARREST_ROLLUPS:
        return str(offense), codes
    return ARREST_CODE_TO_SLUG[codes[0]], codes


@api.get("/agency/{ori}/offenses", response_model=list[OffenseMonthly])
def agency_offenses(ori: Ori, offense: Offense, client: Cde) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        resp = client().summarized_agency(ori, offense.value, LIVE_FROM, LIVE_TO)
        return agency_live.offenses_to_rows(resp)

    return agency_live.fetch(agency_live.cache_key("offenses", ori, offense.value), produce)


@api.get("/agency/{ori}/arrests", response_model=list[ArrestBreakdownRow])
def agency_arrests(
    ori: Ori,
    client: Cde,
    category: CategoryParam = None,
    offense: Annotated[str | None, Query(max_length=40)] = None,
) -> list[dict[str, Any]]:
    # Arrests use a numeric offense code, not a slug: an arrest slug, a
    # summarized slug or a raw code all resolve. A rollup (violent-crime,
    # property-crime) is the sum of its 4 Part I codes, each cached on its own.
    # Anything else is a 422.
    slug, codes = _arrest_codes_or_422(offense)

    def rows_for(code: str) -> list[dict[str, Any]]:
        def produce() -> list[dict[str, Any]]:
            resp = client().arrests_agency(ori, code, from_=LIVE_FROM, to=LIVE_TO)
            if not isinstance(resp, ArrestTotalsResponse):  # type=totals -> totals shape
                return []
            return agency_live.arrests_to_rows(resp)

        return agency_live.fetch(agency_live.cache_key("arrests", ori, code), produce)

    if len(codes) == 1:
        rows = rows_for(codes[0])
    else:
        totals: dict[tuple[str, str], float] = {}
        for code in codes:
            for r in rows_for(code):
                k = (r["category"], r["label"])
                totals[k] = totals.get(k, 0.0) + (r["value"] or 0.0)
        rows = [{"category": c, "label": lbl, "value": v} for (c, lbl), v in totals.items()]
        rows.sort(key=lambda r: (r["category"], -r["value"]))
    derived = len(codes) > 1
    return [
        {**r, "offense": slug, "is_derived": derived}
        for r in agency_live.filter_category(rows, category)
    ]


@api.get("/agency/{ori}/police-employment", response_model=list[PoliceEmploymentRow])
def agency_police_employment(ori: Ori, client: Cde) -> list[dict[str, Any]]:
    state = ori[:2]  # NCIC ORIs are state-prefixed; /pe needs {state}/{ori}

    def produce() -> list[dict[str, Any]]:
        resp = client().police_employment_agency(state, ori, LIVE_FROM_YEAR, LIVE_TO_YEAR)
        return agency_live.pe_to_rows(resp)

    return agency_live.fetch(agency_live.cache_key("pe", ori), produce)


@api.get("/agency/{ori}/hate-crime", response_model=list[ArrestRow])
def agency_hate_crime(
    ori: Ori, client: Cde, category: CategoryParam = None
) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        resp = client().hate_crime_agency(ori, LIVE_FROM, LIVE_TO)
        return agency_live.breakdowns_to_rows(resp.breakdowns)

    rows = agency_live.fetch(agency_live.cache_key("hate-crime", ori), produce)
    return agency_live.filter_category(rows, category)


@api.get("/agency/{ori}/shr", response_model=list[ArrestRow])
def agency_shr(ori: Ori, client: Cde, category: CategoryParam = None) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        resp = client().shr_agency(ori, LIVE_FROM, LIVE_TO)
        return agency_live.breakdowns_to_rows(resp.breakdowns)

    rows = agency_live.fetch(agency_live.cache_key("shr", ori), produce)
    return agency_live.filter_category(rows, category)


PropertyOffense = Enum(  # type: ignore[misc]
    "PropertyOffense", {code: code for code in EXPANDED_PROPERTY_OFFENSES}, type=str
)


@api.get("/agency/{ori}/property", response_model=list[ArrestRow])
def agency_property(
    ori: Ori,
    client: Cde,
    offense: PropertyOffense = PropertyOffense("NB"),  # noqa: B008
    category: CategoryParam = None,
) -> list[dict[str, Any]]:
    code = str(offense.value)

    def produce() -> list[dict[str, Any]]:
        resp = client().property_agency(ori, code, LIVE_FROM, LIVE_TO)
        return agency_live.breakdowns_to_rows(resp.breakdowns)

    rows = agency_live.fetch(agency_live.cache_key("property", ori, code), produce)
    return agency_live.filter_category(rows, category)


@api.get("/agency/{ori}/nibrs", response_model=list[ArrestRow])
def agency_nibrs(
    ori: Ori,
    client: Cde,
    offense: Annotated[str, Query(max_length=4)] = "13A",
    category: CategoryParam = None,
) -> list[dict[str, Any]]:
    code = offense.upper()
    if code not in NIBRS_OFFENSE_CODES:
        raise HTTPException(status_code=422, detail=f"Unknown NIBRS offense code {offense!r}.")

    def produce() -> list[dict[str, Any]]:
        resp = client().nibrs_agency(ori, code, LIVE_FROM, LIVE_TO)
        return agency_live.breakdowns_to_rows(resp.breakdowns)

    rows = agency_live.fetch(agency_live.cache_key("nibrs", ori, code), produce)
    return agency_live.filter_category(rows, category)


app.include_router(api, prefix="/api/v1")
app.include_router(api, prefix="/api", include_in_schema=False, deprecated=True)

# In production the built frontend is mounted at the root (path set via env in
# the Docker image). The API routes above are registered first, so they take
# precedence over this catch-all static mount.
_static_dir = os.getenv("OPENHYDRA_STATIC_DIR")
if _static_dir and Path(_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


def run() -> None:
    import uvicorn

    uvicorn.run(
        "openhydra_api.main:app",
        host="127.0.0.1",
        port=int(os.getenv("PORT", "8000")),
        access_log=False,  # obs.RequestContextMiddleware writes the access log.
    )
