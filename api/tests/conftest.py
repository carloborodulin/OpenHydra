from __future__ import annotations

from collections.abc import Iterator

import duckdb
import pytest
from fastapi.testclient import TestClient

from openhydra_api import agency_live
from openhydra_api.db import get_conn
from openhydra_api.live_guard import LiveGuard
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
            clearances_rate double, clearances_actual double, clearance_ratio double,
            ttm_months bigint default 12, ttm_rate double, yoy_delta double, index_2019 double
        );
        insert into fct_offenses_monthly
            (level, area, offense, period, offenses_rate, offenses_actual, clearances_rate,
             clearances_actual, clearance_ratio, ttm_rate, yoy_delta, index_2019)
        values
            ('national','US','homicide', date '2020-01-01',
                0.5, 1300, 0.26, 670, 0.515, 0.48, 0.10, 120.0),
            ('national','US','homicide', date '2020-02-01',
                0.4, 1100, 0.22, 560, 0.509, 0.46, 0.08, 110.0),
            ('state','NY','homicide', date '2020-01-01',
                0.3, 80, 0.20, 40, 0.500, 0.30, NULL, 95.0);

        create table meta_snapshot as select
            '20261123T000000Z' as release_id,
            timestamp '2026-11-23 00:00:00' as promoted_at,
            timestamp '2026-06-09 00:00:00' as extracted_at_min,
            timestamp '2026-11-22 12:00:00' as extracted_at_max,
            '01-2015' as window_from,
            '12-2024' as window_to,
            'FBI Crime Data Explorer API' as source,
            false as reconstructed;

        create table meta_snapshot_domains as select * from (values
            ('summarized', timestamp '2026-11-22 12:00:00', '01-2015', '12-2024', 3, 'ok'),
            ('lesdc', timestamp '2026-06-10 00:00:00', '2022', '2023', 2, 'ok')
        ) t(domain, extracted_at, window_from, window_to, row_count, status);

        create table dim_agencies(
            ori varchar, agency_name varchar, agency_type varchar, county varchar,
            state_abbr varchar, state_name varchar, latitude double, longitude double,
            is_nibrs boolean, nibrs_start_year integer
        );
        insert into dim_agencies values
            ('NY001','Test PD','City','ERIE','NY','New York', 42.0, -78.0, true, 2021);

        create table fct_arrests(
            level varchar, area varchar, offense varchar, arrest_code varchar,
            window_from varchar default '01-2015', window_to varchar default '12-2024',
            category varchar, label varchar, value double, is_derived boolean
        );
        insert into fct_arrests
            (level, area, offense, arrest_code, category, label, value, is_derived)
        values
            ('national','US','all','all', 'Arrestee Sex','Male', 900.0, false),
            ('national','US','all','all', 'Arrestee Sex','Female', 400.0, false),
            ('national','US','homicide','11', 'Arrestee Sex','Male', 100.0, false),
            ('national','US','homicide','11', 'Arrestee Sex','Female', 40.0, false),
            ('national','US','burglary','60', 'Arrestee Sex','Male', 200.0, false),
            ('national','US','burglary','60', 'Arrestee Sex','Female', 80.0, false),
            ('national','US','violent-crime',NULL, 'Arrestee Sex','Male', 150.0, true),
            ('state','NY','all','all', 'Arrestee Sex','Male', 50.0, false);

        create table fct_police_employment(
            level varchar, area varchar, section varchar,
            metric varchar, year integer, value double
        );
        insert into fct_police_employment values
            ('national','US','actual','Male Officers', 2020, 5000.0);

        create table dim_population(
            level varchar, area varchar, year integer, population bigint
        );
        insert into dim_population values
            ('national','US', 2020, 331577720),
            ('state','NY', 2020, 20201230);

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
            level varchar, area varchar, offense varchar, year integer,
            category varchar, label varchar, value double
        );
        insert into fct_property values
            ('national','US','NB', 2024,'stolen_value','Miscellaneous', 1465971185687.0),
            ('national','US','NB', 2024,'stolen_value','Firearms', 14479512996.0),
            ('national','US','NB', 2023,'stolen_value','Firearms', 1.0),
            ('national','US','NL', NULL,'stolen_value','Currency, Notes, etc.', 500.0);

        create table fct_nibrs(
            level varchar, area varchar, offense varchar,
            category varchar, label varchar, value double
        );
        insert into fct_nibrs values
            ('national','US','13A','offense_weapons','Handgun', 414248.0),
            ('national','US','13A','offense_weapons','Firearm', 257269.0),
            ('national','US','220','victim_location','Residence', 100.0);

        create table fct_lesdc(
            year integer, chart_type varchar, section varchar, label varchar, value double
        );
        insert into fct_lesdc values
            (2022,'manner','S','Firearm', 42.0),
            (2022,'manner','S','Hanging', 4.0),
            (2022,'manner','AS','Overdose of prescription drugs', 4.0);

        create table fct_uof_participation(
            year integer, participating_agencies double,
            total_agencies double, participation_percent double
        );
        insert into fct_uof_participation values
            (2021, 8929.0, 18514.0, 65.0),
            (2022, 10353.0, 18514.0, 75.0);

        create table fct_uof_questions(
            year integer, category varchar, label varchar, value double
        );
        insert into fct_uof_questions values
            (2022,'force','Baton', 9.0),
            (2022,'force','Canine', 4.0),
            (2022,'report','Death of a person due to law enforcement use of force', 31.0);

        create table fct_nibrs_estimation(
            level varchar, area varchar, offense varchar,
            category varchar, label varchar, value double,
            lower double default null, upper double default null
        );
        insert into fct_nibrs_estimation values
            ('national','US','55','Victim_Victim race','White', 12345.0, 11000.0, 13700.0),
            ('national','US','55','Victim_Victim race','Black or African American', 6789.0,
                NULL, NULL),
            ('region','Midwest','55','Victim_Victim race','White', 3000.0, NULL, NULL);
        """
    )
    con.close()

    ro = duckdb.connect(str(db), read_only=True)

    def _override() -> Iterator[duckdb.DuckDBPyConnection]:
        yield ro

    app.dependency_overrides[get_conn] = _override
    with TestClient(app) as c:
        c.db_path = db  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()
    ro.close()


@pytest.fixture
def live_db(tmp_path) -> Iterator[None]:
    """A temp DuckDB that knows the agency NY0303000, for the live routes."""
    db = tmp_path / "live.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        """
        create table dim_agencies(
            ori varchar, agency_name varchar, agency_type varchar, county varchar,
            state_abbr varchar, state_name varchar, latitude double, longitude double,
            is_nibrs boolean, nibrs_start_year integer
        );
        insert into dim_agencies values
            ('NY0303000','Test PD','City','ERIE','NY','New York', 42.0, -78.0, true, 2021),
            ('NY0303001','Other PD','City','ERIE','NY','New York', 42.1, -78.1, true, 2021);
        """
    )
    con.close()
    ro = duckdb.connect(str(db), read_only=True)

    def _override() -> Iterator[duckdb.DuckDBPyConnection]:
        yield ro

    app.dependency_overrides[get_conn] = _override
    yield
    app.dependency_overrides.pop(get_conn, None)
    ro.close()


@pytest.fixture(autouse=True)
def fresh_live_guard(monkeypatch: pytest.MonkeyPatch) -> LiveGuard:
    """Each test gets its own generous live limits and an empty live cache."""
    g = LiveGuard(client_per_min=10_000, global_per_hour=100_000, concurrency=8)
    monkeypatch.setattr(agency_live, "guard", g)
    agency_live.clear_cache()
    return g
