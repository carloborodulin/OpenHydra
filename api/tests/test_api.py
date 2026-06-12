from __future__ import annotations

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["offense_rows"] == 3


def test_meta(client: TestClient) -> None:
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert "homicide" in body["offenses"]
    assert "NY" in body["states"]
    assert body["levels"] == ["national", "state", "agency"]
    # Full 48-code arrest taxonomy is advertised, plus the categories present.
    assert len(body["arrest_offenses"]) == 48
    drugs = next(o for o in body["arrest_offenses"] if o["slug"] == "drug-abuse-violations")
    assert drugs["code"] == "150"
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
    # region geography isolates a different estimate
    mw = client.get(
        "/api/nibrs-estimation", params={"level": "region", "area": "Midwest", "offense": "55"}
    )
    assert mw.json()[0]["value"] == 3000.0
