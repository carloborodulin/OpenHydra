"""Tests for the live agency drill-down routes (proxied from the CDE API)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from cdeclient import CdeConfigError, CdeUpstreamError
from cdeclient.models import (
    ArrestTotalsResponse,
    ChartResponse,
    HateCrimeResponse,
    NibrsResponse,
    PropertyResponse,
    ShrResponse,
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
        shr: Any = None,
        property_: Any = None,
        nibrs: Any = None,
    ) -> None:
        self._summarized = summarized
        self._arrests = arrests
        self._pe = pe
        self._hate_crime = hate_crime
        self._shr = shr
        self._property = property_
        self._nibrs = nibrs
        self.calls = {
            "summarized": 0,
            "arrests": 0,
            "pe": 0,
            "hate_crime": 0,
            "shr": 0,
            "property": 0,
            "nibrs": 0,
        }

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

    def shr_agency(self, ori: str, from_: str, to: str) -> Any:
        self.calls["shr"] += 1
        return _resolve(self._shr)

    def property_agency(self, ori: str, offense: str, from_: str, to: str) -> Any:
        self.calls["property"] += 1
        return _resolve(self._property)

    def nibrs_agency(self, ori: str, offense: str, from_: str, to: str) -> Any:
        self.calls["nibrs"] += 1
        return _resolve(self._nibrs)


def _resolve(value: Any) -> Any:
    if isinstance(value, Exception):
        raise value
    return value


@pytest.fixture
def make_client(live_db):
    """Build a TestClient whose get_cde_client yields the given FakeCde."""
    created: list[TestClient] = []

    def _make(fake: FakeCde) -> TestClient:
        agency_live.clear_cache()
        # Routes get a provider and call it only on a cache miss.
        app.dependency_overrides[cde.get_cde_client] = lambda: lambda: fake
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


def test_agency_offenses_upstream_error_is_502_and_uncached(make_client) -> None:
    fake = FakeCde(summarized=CdeUpstreamError(500, "summarized/agency/NY0303000/homicide"))
    c = make_client(fake)
    r = c.get("/api/agency/NY0303000/offenses", params={"offense": "homicide"})
    assert r.status_code == 502
    assert r.json()["code"] == "upstream_error"
    c.get("/api/agency/NY0303000/offenses", params={"offense": "homicide"})
    assert fake.calls["summarized"] == 2  # errors are not cached → retried


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


def test_agency_shr_breakdowns(make_client) -> None:
    fake = FakeCde(shr=ShrResponse.model_validate(_sample("shr_agency_totals")))
    r = make_client(fake).get("/api/agency/NY0303000/shr", params={"category": "offense_weapons"})
    assert r.status_code == 200
    rows = r.json()
    assert rows and {row["category"] for row in rows} == {"offense_weapons"}
    assert rows == sorted(rows, key=lambda x: -x["value"])


def test_agency_property_breakdowns(make_client) -> None:
    fake = FakeCde(
        property_=PropertyResponse.model_validate(_sample("supplemental_agency_NB_totals"))
    )
    r = make_client(fake).get(
        "/api/agency/NY0303000/property", params={"offense": "NB", "category": "stolen_value"}
    )
    assert r.status_code == 200
    rows = r.json()
    assert rows and {row["category"] for row in rows} == {"stolen_value"}
    assert rows == sorted(rows, key=lambda x: -x["value"])


def test_agency_nibrs_breakdowns(make_client) -> None:
    fake = FakeCde(nibrs=NibrsResponse.model_validate(_sample("nibrs_agency_13A_totals")))
    r = make_client(fake).get(
        "/api/agency/NY0303000/nibrs", params={"offense": "13A", "category": "victim_location"}
    )
    assert r.status_code == 200
    rows = r.json()
    assert rows and {row["category"] for row in rows} == {"victim_location"}
    assert rows == sorted(rows, key=lambda x: -x["value"])


# -- police employment ------------------------------------------------------
def test_agency_police_employment(make_client) -> None:
    fake = FakeCde(pe=ChartResponse.model_validate(_sample("pe_state_NY")))
    r = make_client(fake).get("/api/agency/NY0303000/police-employment")
    assert r.status_code == 200
    rows = r.json()
    assert rows and {"Male Officers", "Female Officers"} <= {row["metric"] for row in rows}


# -- no key configured ------------------------------------------------------
def test_missing_api_key_returns_503(monkeypatch, live_db) -> None:
    # With no override, the provider builds the shared CdeClient; force the
    # no-key error path and assert a clean 503.
    def _boom(*a: Any, **k: Any) -> Any:
        raise CdeConfigError("No API key.")

    cde.close_shared_client()
    agency_live.clear_cache()
    monkeypatch.setattr(cde, "CdeClient", _boom)
    app.dependency_overrides.pop(cde.get_cde_client, None)
    r = TestClient(app).get("/api/agency/NY0303000/police-employment")
    assert r.status_code == 503
    assert r.json()["code"] == "live_data_unconfigured"


def test_agency_arrest_rollup_sums_its_components(make_client) -> None:
    resp = ArrestTotalsResponse.model_validate(_sample("arrest_state_NY_all"))
    fake = FakeCde(arrests=resp)
    c = make_client(fake)
    single = c.get(
        "/api/agency/NY0303000/arrests", params={"offense": "homicide", "category": "Arrestee Sex"}
    ).json()
    rollup = c.get(
        "/api/agency/NY0303000/arrests",
        params={"offense": "violent-crime", "category": "Arrestee Sex"},
    ).json()
    # The fake returns the same payload for each code, so the rollup is 4 times one code.
    by_label = {r["label"]: r["value"] for r in single}
    assert {r["label"]: r["value"] for r in rollup} == {k: 4 * v for k, v in by_label.items()}
    assert all(r["offense"] == "violent-crime" and r["is_derived"] for r in rollup)
    assert all(r["offense"] == "homicide" and not r["is_derived"] for r in single)
    # 4 component codes, and homicide (code 11) was already cached.
    assert fake.calls["arrests"] == 4
