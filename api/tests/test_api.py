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


def test_offenses_monthly(client: TestClient) -> None:
    r = client.get("/api/offenses/monthly", params={"offense": "homicide"})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2  # two national homicide months
    assert rows[0]["period"] == "2020-01-01"
    assert rows[0]["clearance_ratio"] == 0.515


def test_offenses_monthly_404(client: TestClient) -> None:
    r = client.get("/api/offenses/monthly", params={"offense": "does-not-exist"})
    assert r.status_code == 404


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
