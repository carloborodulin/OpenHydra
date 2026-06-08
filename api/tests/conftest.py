from __future__ import annotations

from collections.abc import Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from openhydra_api.db import get_conn
from openhydra_api.main import app


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    """A TestClient wired to a tiny temp DuckDB with the four mart tables."""
    db = tmp_path / "test.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        """
        create table fct_offenses_monthly(
            level varchar, area varchar, offense varchar, period date,
            offenses_rate double, offenses_actual double,
            clearances_rate double, clearances_actual double, clearance_ratio double
        );
        insert into fct_offenses_monthly values
            ('national','US','homicide', date '2020-01-01', 0.5, 1300, 0.26, 670, 0.515),
            ('national','US','homicide', date '2020-02-01', 0.4, 1100, 0.22, 560, 0.509),
            ('state','NY','homicide',    date '2020-01-01', 0.3,  80,  0.20,  40, 0.500);

        create table dim_agencies(
            ori varchar, agency_name varchar, agency_type varchar, county varchar,
            state_abbr varchar, state_name varchar, latitude double, longitude double,
            is_nibrs boolean, nibrs_start_year integer
        );
        insert into dim_agencies values
            ('NY001','Test PD','City','ERIE','NY','New York', 42.0, -78.0, true, 2021);

        create table fct_arrests(
            level varchar, area varchar, category varchar, label varchar, value double
        );
        insert into fct_arrests values
            ('national','US','Arrestee Sex','Male', 100.0),
            ('national','US','Arrestee Sex','Female', 40.0);

        create table fct_police_employment(
            level varchar, area varchar, section varchar,
            metric varchar, year integer, value double
        );
        insert into fct_police_employment values
            ('national','US','actual','Male Officers', 2020, 5000.0);
        """
    )
    con.close()

    ro = duckdb.connect(str(db), read_only=True)

    def _override() -> Iterator[duckdb.DuckDBPyConnection]:
        yield ro

    app.dependency_overrides[get_conn] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    ro.close()
