"""FastAPI app serving the OpenHydra DuckDB marts as JSON."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

import duckdb
from cdeclient import CdeClient, CdeError
from cdeclient.constants import ARREST_OFFENSES, arrest_code
from cdeclient.models import ArrestTotalsResponse
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import agency_live
from .cde import get_cde_client
from .db import get_conn
from .models import (
    AgencyFeature,
    ArrestOffense,
    ArrestRow,
    Meta,
    OffenseMonthly,
    PoliceEmploymentRow,
)

# Request-scoped read-only DuckDB connection (FastAPI Annotated dependency).
Conn = Annotated[duckdb.DuckDBPyConnection, Depends(get_conn)]
# Request-scoped live CDE client for agency drill-down.
Cde = Annotated[CdeClient, Depends(get_cde_client)]

# Window for live agency calls (mirrors the ETL defaults). Most endpoints take
# MM-YYYY; /pe takes 4-digit years.
LIVE_FROM, LIVE_TO = "01-2020", "12-2022"
LIVE_FROM_YEAR, LIVE_TO_YEAR = "2020", "2022"

# Live agency calls degrade to empty rows on these: gateway/network hiccups
# (CdeError) or an unexpected/sparse response shape (ValidationError).
LIVE_ERRORS = (CdeError, ValidationError)

app = FastAPI(
    title="OpenHydra API",
    version="0.1.0",
    description="Read-only access to FBI UCR crime marts (DuckDB).",
)

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
    arrest_offenses = [
        ArrestOffense(slug=slug, code=info.code, name=info.name, category=info.category)
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
               clearances_rate, clearances_actual, clearance_ratio
        from fct_offenses_monthly
        where level = ? and area = ? and offense = ?
        order by period
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


@app.get("/api/arrests", response_model=list[ArrestRow])
def arrests(
    conn: Conn,
    level: str = "national",
    area: str = "US",
    offense: str | None = None,
    category: str | None = None,
) -> list[dict[str, Any]]:
    sql = "select category, label, value from fct_arrests where level = ? and area = ?"
    params: list[Any] = [level, area]
    if offense:
        sql += " and offense = ?"
        params.append(offense)
    if category:
        sql += " and category = ?"
        params.append(category)
    sql += " order by category, value desc"
    return _dicts(conn, sql, params)


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


# -- agency drill-down (live, proxied from the CDE API) --------------------
# The warehouse only holds national + state rows. Per-agency data for ~19,619
# agencies can't be pre-materialized, so these routes fetch live via cdeclient
# and normalize to the same row shapes the warehouse routes return, with a small
# TTL cache in front (see agency_live).


@app.get("/api/agency/{ori}/offenses", response_model=list[OffenseMonthly])
def agency_offenses(ori: str, offense: str, client: Cde) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        try:
            resp = client.summarized_agency(ori, offense, LIVE_FROM, LIVE_TO)
        except LIVE_ERRORS:
            return []
        return agency_live.offenses_to_rows(resp)

    return agency_live.cached(agency_live.cache_key("offenses", ori, offense), produce)


@app.get("/api/agency/{ori}/arrests", response_model=list[ArrestRow])
def agency_arrests(
    ori: str,
    client: Cde,
    category: str | None = None,
    offense: str | None = None,
) -> list[dict[str, Any]]:
    # Arrests use a numeric offense code, not a slug (same resolver the ETL uses):
    # an arrest slug, a summarized slug, or a raw code all resolve; unknown -> "all".
    code = arrest_code(offense)

    def produce() -> list[dict[str, Any]]:
        try:
            resp = client.arrests_agency(ori, code, from_=LIVE_FROM, to=LIVE_TO)
        except LIVE_ERRORS:
            return []
        if not isinstance(resp, ArrestTotalsResponse):  # type=totals -> totals shape
            return []
        return agency_live.arrests_to_rows(resp, category)

    return agency_live.cached(agency_live.cache_key("arrests", ori, code, category), produce)


@app.get("/api/agency/{ori}/police-employment", response_model=list[PoliceEmploymentRow])
def agency_police_employment(ori: str, client: Cde) -> list[dict[str, Any]]:
    state = ori[:2]  # NCIC ORIs are state-prefixed; /pe needs {state}/{ori}

    def produce() -> list[dict[str, Any]]:
        try:
            resp = client.police_employment_agency(state, ori, LIVE_FROM_YEAR, LIVE_TO_YEAR)
        except LIVE_ERRORS:
            return []
        return agency_live.pe_to_rows(resp)

    return agency_live.cached(agency_live.cache_key("pe", ori), produce)


@app.get("/api/agency/{ori}/hate-crime", response_model=list[ArrestRow])
def agency_hate_crime(
    ori: str,
    client: Cde,
    category: str | None = None,
) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        try:
            resp = client.hate_crime_agency(ori, LIVE_FROM, LIVE_TO)
        except LIVE_ERRORS:
            return []
        return agency_live.breakdowns_to_rows(resp.breakdowns, category)

    return agency_live.cached(agency_live.cache_key("hate-crime", ori, category), produce)


@app.get("/api/agency/{ori}/shr", response_model=list[ArrestRow])
def agency_shr(
    ori: str,
    client: Cde,
    category: str | None = None,
) -> list[dict[str, Any]]:
    def produce() -> list[dict[str, Any]]:
        try:
            resp = client.shr_agency(ori, LIVE_FROM, LIVE_TO)
        except LIVE_ERRORS:
            return []
        return agency_live.breakdowns_to_rows(resp.breakdowns, category)

    return agency_live.cached(agency_live.cache_key("shr", ori, category), produce)


# In production the built frontend is mounted at the root (path set via env in
# the Docker image). The API routes above are registered first, so they take
# precedence over this catch-all static mount.
_static_dir = os.getenv("OPENHYDRA_STATIC_DIR")
if _static_dir and Path(_static_dir).is_dir():
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


def run() -> None:
    import uvicorn

    uvicorn.run("openhydra_api.main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8000")))
