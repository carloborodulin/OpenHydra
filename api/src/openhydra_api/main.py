"""FastAPI app serving the OpenHydra DuckDB marts as JSON."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import duckdb
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
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi import Path as FastPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import agency_live, obs
from .cde import ClientProvider, close_shared_client, get_cde_client
from .db import get_conn
from .models import (
    AgencyFeature,
    ArrestAvailability,
    ArrestBreakdownRow,
    ArrestOffense,
    ArrestRow,
    BenchmarkRow,
    LesdcRow,
    Meta,
    OffenseMonthly,
    PoliceEmploymentRow,
    PopulationRow,
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
obs.install(app)

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


@app.get("/health")
def health(conn: Conn) -> dict[str, Any]:
    row = conn.execute("select count(*) from fct_offenses_monthly").fetchone()
    return {"status": "ok", "offense_rows": row[0] if row else 0}


@app.get("/api/meta", response_model=Meta)
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
        offenses=offenses,
        states=states,
        levels=["national", "state", "agency"],
        arrest_offenses=arrest_offenses,
        arrest_categories=arrest_categories,
    )


@app.get("/api/offenses/monthly", response_model=list[OffenseMonthly])
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
               ttm_rate, yoy_delta, index_2019
        from fct_offenses_monthly
        where level = ? and area = ? and offense = ?
        order by period
        """,
        [level, area, offense],
    )
    if not rows:
        raise HTTPException(status_code=404, detail="no data for that level/area/offense")
    return rows


@app.get("/api/offenses/benchmark", response_model=list[BenchmarkRow])
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


@app.get("/api/agencies", response_model=list[AgencyFeature])
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


@app.get("/api/arrests", response_model=list[ArrestBreakdownRow])
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


@app.get("/api/arrests/available", response_model=ArrestAvailability)
def arrests_available(conn: Conn, level: str = "national", area: str = "US") -> dict[str, Any]:
    """The arrest offenses that have rows in the snapshot for one scope."""
    rows = conn.execute(
        "select distinct offense from fct_arrests where level = ? and area = ? order by 1",
        [level, area],
    ).fetchall()
    return {"level": level, "area": area, "offenses": [r[0] for r in rows]}


@app.get("/api/police-employment", response_model=list[PoliceEmploymentRow])
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


@app.get("/api/population", response_model=list[PopulationRow])
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


@app.get("/api/hate-crime", response_model=list[ArrestRow])
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


@app.get("/api/shr", response_model=list[ArrestRow])
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


@app.get("/api/property", response_model=list[ArrestRow])
def expanded_property(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    offense: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    # Expanded property (supplemental); `offense` is NB/NL/NMVT/NROB, `category`
    # the value/count dimension (stolen_value, recovered_value, location_counts…).
    sql = "select category, label, value from fct_property where level = ? and area = ?"
    params: list[Any] = [level, area]
    if offense:
        sql += " and offense = ?"
        params.append(offense)
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


@app.get("/api/nibrs", response_model=list[ArrestRow])
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


@app.get("/api/lesdc", response_model=list[LesdcRow])
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


@app.get("/api/uof/participation", response_model=list[UofParticipationRow])
def uof_participation(conn: Conn) -> list[dict[str, Any]]:
    # Use-of-Force national reporting participation, one row per year.
    return _dicts(
        conn,
        "select year, participating_agencies, total_agencies, participation_percent "
        "from fct_uof_participation order by year",
    )


@app.get("/api/uof/questions", response_model=list[ArrestRow])
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


@app.get("/api/nibrs-estimation", response_model=list[ArrestRow])
def nibrs_estimation(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    offense: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    # Modeled (estimated) NIBRS counts; level is national|region, `offense` a
    # numeric estimation code, `category` the section_dimension.
    sql = "select category, label, value from fct_nibrs_estimation where level = ? and area = ?"
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

OriParam = Annotated[
    str,
    FastPath(
        pattern=r"^[A-Za-z]{2}[A-Za-z0-9]{7}$",
        description="A 9-character NCIC ORI, for example NY0303000.",
    ),
]
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


@app.get("/api/agency/{ori}/offenses", response_model=list[OffenseMonthly])
def agency_offenses(ori: Ori, offense: Offense, client: Cde) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        resp = client().summarized_agency(ori, offense.value, LIVE_FROM, LIVE_TO)
        return agency_live.offenses_to_rows(resp)

    return agency_live.fetch(agency_live.cache_key("offenses", ori, offense.value), produce)


@app.get("/api/agency/{ori}/arrests", response_model=list[ArrestBreakdownRow])
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


@app.get("/api/agency/{ori}/police-employment", response_model=list[PoliceEmploymentRow])
def agency_police_employment(ori: Ori, client: Cde) -> list[dict[str, Any]]:
    state = ori[:2]  # NCIC ORIs are state-prefixed; /pe needs {state}/{ori}

    def produce() -> list[dict[str, Any]]:
        resp = client().police_employment_agency(state, ori, LIVE_FROM_YEAR, LIVE_TO_YEAR)
        return agency_live.pe_to_rows(resp)

    return agency_live.fetch(agency_live.cache_key("pe", ori), produce)


@app.get("/api/agency/{ori}/hate-crime", response_model=list[ArrestRow])
def agency_hate_crime(
    ori: Ori, client: Cde, category: CategoryParam = None
) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        resp = client().hate_crime_agency(ori, LIVE_FROM, LIVE_TO)
        return agency_live.breakdowns_to_rows(resp.breakdowns)

    rows = agency_live.fetch(agency_live.cache_key("hate-crime", ori), produce)
    return agency_live.filter_category(rows, category)


@app.get("/api/agency/{ori}/shr", response_model=list[ArrestRow])
def agency_shr(ori: Ori, client: Cde, category: CategoryParam = None) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        resp = client().shr_agency(ori, LIVE_FROM, LIVE_TO)
        return agency_live.breakdowns_to_rows(resp.breakdowns)

    rows = agency_live.fetch(agency_live.cache_key("shr", ori), produce)
    return agency_live.filter_category(rows, category)


PropertyOffense = Enum(  # type: ignore[misc]
    "PropertyOffense", {code: code for code in EXPANDED_PROPERTY_OFFENSES}, type=str
)


@app.get("/api/agency/{ori}/property", response_model=list[ArrestRow])
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


@app.get("/api/agency/{ori}/nibrs", response_model=list[ArrestRow])
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
