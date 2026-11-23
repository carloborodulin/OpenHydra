from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "release_id": "20261123T000000Z"}


def test_health_is_503_for_an_empty_mart(tmp_path, monkeypatch) -> None:
    import duckdb

    from openhydra_api.db import get_conn
    from openhydra_api.main import REQUIRED_TABLES, app

    db = tmp_path / "empty.duckdb"
    con = duckdb.connect(str(db))
    for table in REQUIRED_TABLES:
        con.execute(f"create table {table} (x integer)")
        if table != "fct_arrests":
            con.execute(f"insert into {table} values (1)")
    con.close()
    ro = duckdb.connect(str(db), read_only=True)
    app.dependency_overrides[get_conn] = lambda: (yield ro)
    try:
        r = TestClient(app).get("/health")
    finally:
        app.dependency_overrides.clear()
        ro.close()
    assert r.status_code == 503
    assert r.json() == {"status": "invalid_snapshot", "problems": ["fct_arrests: no rows"]}


def test_missing_warehouse_is_a_clean_503(monkeypatch, tmp_path) -> None:
    from openhydra_api.main import app

    monkeypatch.setenv("OPENHYDRA_DUCKDB", str(tmp_path / "absent.duckdb"))
    r = TestClient(app).get("/health")
    assert r.status_code == 503
    assert r.json()["code"] == "warehouse_unavailable"
    assert "absent.duckdb" not in r.text


def test_meta_snapshot_and_capabilities(client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("FBI_CDE_API_KEY", raising=False)
    monkeypatch.setenv("OPENHYDRA_ENV_FILE", "/nonexistent/.env")
    body = client.get("/api/meta").json()
    assert body["snapshot"]["release_id"] == "20261123T000000Z"
    assert body["snapshot"]["window_from"] == "01-2015"
    assert body["snapshot"]["reconstructed"] is False
    lesdc = next(d for d in body["snapshot"]["domains"] if d["domain"] == "lesdc")
    assert (lesdc["window_from"], lesdc["window_to"]) == ("2022", "2023")
    assert body["capabilities"] == {"live_agency": False}
    monkeypatch.setenv("FBI_CDE_API_KEY", "synthetic")
    assert client.get("/api/meta").json()["capabilities"] == {"live_agency": True}


def test_meta(client: TestClient) -> None:
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert "homicide" in body["offenses"]
    assert "NY" in body["states"]
    assert body["levels"] == ["national", "state", "agency"]
    # The 48-code arrest taxonomy plus the 2 derived rollups, each flagged with
    # whether the national snapshot holds it.
    offenses = {o["slug"]: o for o in body["arrest_offenses"]}
    assert len(offenses) == 50
    assert offenses["drug-abuse-violations"]["code"] == "150"
    assert offenses["drug-abuse-violations"]["in_snapshot"] is False
    assert offenses["homicide"]["in_snapshot"] is True
    assert offenses["violent-crime"]["derived"] is True
    assert offenses["violent-crime"]["in_snapshot"] is True
    assert offenses["property-crime"]["in_snapshot"] is False
    assert "Arrestee Sex" in body["arrest_categories"]


def test_offenses_monthly(client: TestClient) -> None:
    r = client.get("/api/offenses/monthly", params={"offense": "homicide"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2  # two national homicide months
    assert rows[0]["period"] == "2020-01-01"
    assert rows[0]["clearance_ratio"] == 0.515
    # Trailing-12-month trend metrics are surfaced alongside the base series.
    assert rows[0]["yoy_delta"] == 0.10
    assert rows[0]["index_2019"] == 120.0
    assert rows[0]["ttm_rate"] == 0.48


def test_offenses_monthly_404(client: TestClient) -> None:
    r = client.get("/api/offenses/monthly", params={"offense": "does-not-exist"})
    assert r.status_code == 404


def test_population(client: TestClient) -> None:
    r = client.get("/api/population", params={"level": "national", "area": "US"})
    assert r.status_code == 200
    rows = r.json()
    assert rows == [{"year": 2020, "population": 331577720}]


def test_offenses_benchmark(client: TestClient) -> None:
    # NY homicide rate 0.3 vs national 0.5 for 2020-01 -> relative index 60.
    r = client.get(
        "/api/offenses/benchmark",
        params={"offense": "homicide", "level": "state", "area": "NY"},
    )
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["area_rate"] == 0.3
    assert rows[0]["national_rate"] == 0.5
    assert rows[0]["relative_index"] == 60.0


def test_agencies_filtered(client: TestClient) -> None:
    r = client.get("/api/agencies", params={"state": "ny"})
    assert r.status_code == 200
    rows = r.json()
    assert rows[0]["ori"] == "NY001"
    assert rows[0]["is_nibrs"] is True
    assert rows[0]["nibrs_start_year"] == 2021


def test_arrests(client: TestClient) -> None:
    r = client.get("/api/arrests", params={"offense": "homicide", "category": "Arrestee Sex"})
    assert r.status_code == 200
    rows = r.json()
    assert {row["label"] for row in rows} == {"Male", "Female"}
    assert rows[0]["value"] == 100.0  # ordered by value desc


def test_arrests_default_is_all_offenses_with_offense_column(client: TestClient) -> None:
    rows = client.get("/api/arrests", params={"category": "Arrestee Sex"}).json()
    # One row per label: the default never mixes offense codes.
    assert [(r["offense"], r["label"], r["value"]) for r in rows] == [
        ("all", "Male", 900.0),
        ("all", "Female", 400.0),
    ]


def test_arrest_rollup_rows_are_flagged(client: TestClient) -> None:
    rows = client.get("/api/arrests", params={"offense": "violent-crime"}).json()
    assert rows and all(r["is_derived"] for r in rows)


def test_every_available_arrest_offense_has_rows(client: TestClient) -> None:
    # The selector shows only the offenses this route lists for a scope, so each
    # one must return rows (DATA-2).
    for level, area in (("national", "US"), ("state", "NY"), ("state", "TX")):
        avail = client.get("/api/arrests/available", params={"level": level, "area": area})
        assert avail.status_code == 200
        for offense in avail.json()["offenses"]:
            r = client.get(
                "/api/arrests", params={"level": level, "area": area, "offense": offense}
            )
            assert r.json(), (level, area, offense)
    nat = client.get("/api/arrests/available").json()["offenses"]
    assert nat == ["all", "burglary", "homicide", "violent-crime"]
    assert (
        client.get("/api/arrests/available", params={"level": "state", "area": "TX"}).json()[
            "offenses"
        ]
        == []
    )


def test_arrests_offense_filter(client: TestClient) -> None:
    # The same demographic varies by offense — the whole point of the offense filter.
    sex = {"category": "Arrestee Sex"}
    homicide = client.get("/api/arrests", params={"offense": "homicide", **sex})
    burglary = client.get("/api/arrests", params={"offense": "burglary", **sex})
    assert homicide.json()[0]["value"] == 100.0
    assert burglary.json()[0]["value"] == 200.0


def test_police_employment(client: TestClient) -> None:
    r = client.get("/api/police-employment")
    assert r.status_code == 200
    assert r.json()[0]["metric"] == "Male Officers"


def test_hate_crime(client: TestClient) -> None:
    r = client.get("/api/hate-crime", params={"category": "bias_category"})
    assert r.status_code == 200
    rows = r.json()
    assert {row["label"] for row in rows} == {"Race/Ethnicity/Ancestry", "Religion"}
    assert rows[0]["value"] == 20875.0  # ordered by value desc


def test_shr(client: TestClient) -> None:
    r = client.get("/api/shr", params={"category": "offense_weapons"})
    assert r.status_code == 200
    rows = r.json()
    assert {row["label"] for row in rows} == {"Handgun", "Firearm"}
    assert rows[0]["value"] == 23873.0  # Handgun, value desc


def test_property_offense_filter(client: TestClient) -> None:
    r = client.get("/api/property", params={"offense": "NB", "category": "stolen_value"})
    assert r.status_code == 200
    rows = r.json()
    assert {row["label"] for row in rows} == {"Miscellaneous", "Firearms"}
    assert rows[0]["label"] == "Miscellaneous"  # largest stolen value, desc
    # NL has different data — the offense filter isolates it
    nl = client.get("/api/property", params={"offense": "NL", "category": "stolen_value"})
    assert {row["label"] for row in nl.json()} == {"Currency, Notes, etc."}


def test_property_years_and_default_year(client: TestClient) -> None:
    # Without a year, the latest year; with one, that year only.
    rows = client.get("/api/property", params={"offense": "NB"}).json()
    assert {r["year"] for r in rows} == {2024}
    old = client.get("/api/property", params={"offense": "NB", "year": 2023}).json()
    assert [(r["label"], r["value"]) for r in old] == [("Firearms", 1.0)]
    assert client.get("/api/property/years", params={"offense": "NB"}).json() == {
        "years": [2023, 2024],
        "window_total": False,
    }
    # An older snapshot has only window totals (year null).
    nl = client.get("/api/property", params={"offense": "NL"}).json()
    assert [r["year"] for r in nl] == [None]
    assert client.get("/api/property/years", params={"offense": "NL"}).json() == {
        "years": [],
        "window_total": True,
    }


def test_nibrs(client: TestClient) -> None:
    r = client.get("/api/nibrs", params={"offense": "13A", "category": "offense_weapons"})
    assert r.status_code == 200
    rows = r.json()
    assert {row["label"] for row in rows} == {"Handgun", "Firearm"}
    assert rows[0]["value"] == 414248.0  # Handgun, value desc


def test_lesdc(client: TestClient) -> None:
    r = client.get("/api/lesdc", params={"year": 2022, "chart_type": "manner", "section": "S"})
    assert r.status_code == 200
    rows = r.json()
    assert {row["label"] for row in rows} == {"Firearm", "Hanging"}
    assert rows[0]["value"] == 42.0  # Firearm, value desc


def test_uof_participation(client: TestClient) -> None:
    r = client.get("/api/uof/participation")
    assert r.status_code == 200
    rows = r.json()
    assert [row["year"] for row in rows] == [2021, 2022]  # ordered by year
    assert rows[-1]["participation_percent"] == 75.0


def test_uof_questions(client: TestClient) -> None:
    r = client.get("/api/uof/questions", params={"year": 2022, "category": "force"})
    assert r.status_code == 200
    rows = r.json()
    assert {row["label"] for row in rows} == {"Baton", "Canine"}
    assert rows[0]["value"] == 9.0  # Baton, value desc


def test_nibrs_estimation(client: TestClient) -> None:
    r = client.get(
        "/api/nibrs-estimation", params={"offense": "55", "category": "Victim_Victim race"}
    )
    assert r.status_code == 200
    rows = r.json()
    assert {row["label"] for row in rows} == {"White", "Black or African American"}
    assert rows[0]["value"] == 12345.0  # White, value desc
    assert (rows[0]["lower"], rows[0]["upper"]) == (11000.0, 13700.0)  # the FBI interval
    assert rows[1]["lower"] is None  # an older release has no interval
    # region geography isolates a different estimate
    mw = client.get(
        "/api/nibrs-estimation", params={"level": "region", "area": "Midwest", "offense": "55"}
    )
    assert mw.json()[0]["value"] == 3000.0
