"""FastAPI app serving the OpenHydra DuckDB marts as JSON."""

from __future__ import annotations

from typing import Annotated, Any

import duckdb
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .db import get_conn
from .models import AgencyFeature, ArrestRow, Meta, OffenseMonthly, PoliceEmploymentRow

# Request-scoped read-only DuckDB connection (FastAPI Annotated dependency).
Conn = Annotated[duckdb.DuckDBPyConnection, Depends(get_conn)]

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
    return Meta(offenses=offenses, states=states, levels=["national", "state", "agency"])


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
    category: str | None = None,
) -> list[dict[str, Any]]:
    sql = "select category, label, value from fct_arrests where level = ? and area = ?"
    params: list[Any] = [level, area]
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


def run() -> None:
    import uvicorn

    uvicorn.run("openhydra_api.main:app", host="127.0.0.1", port=8000)
