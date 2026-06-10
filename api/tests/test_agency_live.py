"""Tests for the live agency drill-down routes (proxied from the CDE API)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from cdeclient import CdeError
from cdeclient.models import (
    ArrestTotalsResponse,
    ChartResponse,
    HateCrimeResponse,
    SummarizedResponse,
)
from fastapi.testclient import TestClient

from openhydra_api import agency_live, cde
from openhydra_api.main import app

# tests/ -> api/ -> OpenHydra/ -> data/samples
SAMPLES = Path(__file__).resolve().parents[2] / "data" / "samples"


def _sample(name: str) -> Any:
    return json.loads((SAMPLES / f"{name}.json").read_text())


class FakeCde:
    """Stands in for CdeClient; records call counts and returns canned responses."""

    def __init__(
        self,
        summarized: Any = None,
        arrests: Any = None,
        pe: Any = None,
        hate_crime: Any = None,
    ) -> None:
        self._summarized = summarized
        self._arrests = arrests
        self._pe = pe
        self._hate_crime = hate_crime
        self.calls = {"summarized": 0, "arrests": 0, "pe": 0, "hate_crime": 0}

    def summarized_agency(self, ori: str, offense: str, from_: str, to: str) -> Any:
        self.calls["summarized"] += 1
        return _resolve(self._summarized)

    def arrests_agency(
        self, ori: str, offense: str = "all", *, arrest_type: str = "totals", from_: str, to: str
    ) -> Any:
        self.calls["arrests"] += 1
        return _resolve(self._arrests)

    def police_employment_agency(self, state: str, ori: str, from_: str, to: str) -> Any:
        self.calls["pe"] += 1
        return _resolve(self._pe)

    def hate_crime_agency(self, ori: str, from_: str, to: str) -> Any:
        self.calls["hate_crime"] += 1
        return _resolve(self._hate_crime)


def _resolve(value: Any) -> Any:
    if isinstance(value, Exception):
        raise value
    return value


@pytest.fixture
def make_client():
    """Build a TestClient whose get_cde_client yields the given FakeCde."""
    created: list[TestClient] = []

    def _make(fake: FakeCde) -> TestClient:
        agency_live.clear_cache()
        app.dependency_overrides[cde.get_cde_client] = lambda: fake
        c = TestClient(app)
        created.append(c)
        return c

    yield _make
    app.dependency_overrides.clear()
    agency_live.clear_cache()


def _summarized() -> SummarizedResponse:
    return SummarizedResponse.model_validate(_sample("summarized_agency_violent"))


# -- offenses ---------------------------------------------------------------
def test_agency_offenses_pivots_own_series_only(make_client) -> None:
    fake = FakeCde(summarized=_summarized())
    r = make_client(fake).get("/api/agency/NY0303000/offenses", params={"offense": "violent-crime"})
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected non-empty agency offense rows"
    # Every row must carry an actual offense count (proves we kept the agency's
    # own series, which alone appears in `actuals` — not the rates-only benchmarks).
    assert all(row["offenses_actual"] is not None for row in rows)
    # clearance_ratio = clearances_actual / offenses_actual where computable.
    for row in rows:
        if row["offenses_actual"] and row["clearances_actual"] is not None:
            assert row["clearance_ratio"] == pytest.approx(
                row["clearances_actual"] / row["offenses_actual"]
            )


def test_agency_offenses_caches_nonempty(make_client) -> None:
    fake = FakeCde(summarized=_summarized())
    c = make_client(fake)
    c.get("/api/agency/NY0303000/offenses", params={"offense": "violent-crime"})
    c.get("/api/agency/NY0303000/offenses", params={"offense": "violent-crime"})
    assert fake.calls["summarized"] == 1  # second request served from cache


def test_agency_offenses_error_returns_empty_uncached(make_client) -> None:
    fake = FakeCde(summarized=CdeError("boom"))
    c = make_client(fake)
    assert c.get("/api/agency/NY0303000/offenses", params={"offense": "homicide"}).json() == []
    c.get("/api/agency/NY0303000/offenses", params={"offense": "homicide"})
    assert fake.calls["summarized"] == 2  # empties are not cached → retried


# -- arrests ----------------------------------------------------------------
def test_agency_arrests_category_filter_and_slug_mapping(make_client) -> None:
    fake = FakeCde(arrests=ArrestTotalsResponse.model_validate(_sample("arrest_state_NY_all")))
    r = make_client(fake).get(
        "/api/agency/NY0303000/arrests",
        params={"category": "Arrestee Race", "offense": "homicide"},
    )
    assert r.status_code == 200
    rows = r.json()
    assert rows and {row["category"] for row in rows} == {"Arrestee Race"}
    # ordered by value desc within the category
    assert rows == sorted(rows, key=lambda x: -x["value"])


# -- hate crime -------------------------------------------------------------
def test_agency_hate_crime_breakdowns(make_client) -> None:
    fake = FakeCde(hate_crime=HateCrimeResponse.model_validate(_sample("hate_crime_agency")))
    r = make_client(fake).get(
        "/api/agency/NY0303000/hate-crime", params={"category": "bias_category"}
    )
    assert r.status_code == 200
    rows = r.json()
    assert rows and {row["category"] for row in rows} == {"bias_category"}
    assert rows == sorted(rows, key=lambda x: -x["value"])  # value desc within dimension


# -- police employment ------------------------------------------------------
def test_agency_police_employment(make_client) -> None:
    fake = FakeCde(pe=ChartResponse.model_validate(_sample("pe_state_NY")))
    r = make_client(fake).get("/api/agency/NY0303000/police-employment")
    assert r.status_code == 200
    rows = r.json()
    assert rows and {"Male Officers", "Female Officers"} <= {row["metric"] for row in rows}


# -- no key configured ------------------------------------------------------
def test_missing_api_key_returns_503(monkeypatch) -> None:
    # With no override, get_cde_client constructs a real CdeClient; force the
    # no-key error path and assert a clean 503.
    def _boom(*a: Any, **k: Any) -> Any:
        raise CdeError("No API key.")

    monkeypatch.setattr(cde, "CdeClient", _boom)
    app.dependency_overrides.pop(cde.get_cde_client, None)
    r = TestClient(app).get("/api/agency/NY0303000/police-employment")
    assert r.status_code == 503
