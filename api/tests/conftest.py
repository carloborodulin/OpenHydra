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
            level varchar, area varchar, offense varchar,
            category varchar, label varchar, value double
        );
        insert into fct_arrests values
            ('national','US','homicide','Arrestee Sex','Male', 100.0),
            ('national','US','homicide','Arrestee Sex','Female', 40.0),
            ('national','US','burglary','Arrestee Sex','Male', 200.0),
            ('national','US','burglary','Arrestee Sex','Female', 80.0);

        create table fct_police_employment(
            level varchar, area varchar, section varchar,
            metric varchar, year integer, value double
        );
        insert into fct_police_employment values
            ('national','US','actual','Male Officers', 2020, 5000.0);

        create table fct_hate_crime(
            level varchar, area varchar,
            category varchar, label varchar, value double
        );
        insert into fct_hate_crime values
            ('national','US','bias_category','Race/Ethnicity/Ancestry', 20875.0),
            ('national','US','bias_category','Religion', 5708.0),
            ('national','US','offender_race','White', 15430.0);

        create table fct_shr(
            level varchar, area varchar,
            category varchar, label varchar, value double
        );
        insert into fct_shr values
            ('national','US','offense_weapons','Handgun', 23873.0),
            ('national','US','offense_weapons','Firearm', 16498.0),
            ('national','US','victim_race','Black or African American', 31402.0);

        create table fct_property(
            level varchar, area varchar, offense varchar,
            category varchar, label varchar, value double
        );
        insert into fct_property values
            ('national','US','NB','stolen_value','Miscellaneous', 1465971185687.0),
            ('national','US','NB','stolen_value','Firearms', 14479512996.0),
            ('national','US','NL','stolen_value','Currency, Notes, etc.', 500.0);

        create table fct_nibrs(
            level varchar, area varchar, offense varchar,
            category varchar, label varchar, value double
        );
        insert into fct_nibrs values
            ('national','US','13A','offense_weapons','Handgun', 414248.0),
            ('national','US','13A','offense_weapons','Firearm', 257269.0),
            ('national','US','220','victim_location','Residence', 100.0);
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
