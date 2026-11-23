"""Input checks, cache behavior and upstream limits of the live agency routes."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from cdeclient.models import (
    ArrestTotalsResponse,
    HateCrimeResponse,
    SummarizedResponse,
)
from fastapi.testclient import TestClient

from openhydra_api import agency_live, cde
from openhydra_api.agency_live import LiveCache
from openhydra_api.live_guard import LiveGuard, LiveLimitError
from openhydra_api.main import app

from .test_agency_live import FakeCde, _sample

ORI = "NY0303000"


@pytest.fixture
def client_for(live_db: None):
    def _make(fake: Any) -> TestClient:
        app.dependency_overrides[cde.get_cde_client] = lambda: lambda: fake
        return TestClient(app)

    yield _make
    app.dependency_overrides.pop(cde.get_cde_client, None)


def _summarized() -> SummarizedResponse:
    return SummarizedResponse.model_validate(_sample("summarized_agency_violent"))


# -- input checks (no upstream call for a bad request) -----------------------
@pytest.mark.parametrize("bad", ["NY03", "NY0303000X", "NY03-3000", "../x/y/z"])
def test_malformed_ori_is_422_without_upstream_call(client_for: Any, bad: str) -> None:
    fake = FakeCde(summarized=_summarized())
    r = client_for(fake).get(f"/api/agency/{bad}/offenses", params={"offense": "homicide"})
    assert r.status_code in (404, 422)
    assert fake.calls["summarized"] == 0


def test_unknown_ori_is_404_without_upstream_call(client_for: Any) -> None:
    fake = FakeCde(summarized=_summarized())
    r = client_for(fake).get("/api/agency/ZZ9999999/offenses", params={"offense": "homicide"})
    assert r.status_code == 404
    assert fake.calls["summarized"] == 0


def test_lower_case_ori_is_canonical(client_for: Any) -> None:
    fake = FakeCde(summarized=_summarized())
    c = client_for(fake)
    assert c.get(f"/api/agency/{ORI}/offenses", params={"offense": "homicide"}).status_code == 200
    assert (
        c.get(f"/api/agency/{ORI.lower()}/offenses", params={"offense": "homicide"}).status_code
        == 200
    )
    assert fake.calls["summarized"] == 1  # one canonical cache key


@pytest.mark.parametrize(
    ("route", "params", "kw"),
    [
        ("offenses", {"offense": "not-an-offense"}, "summarized"),
        ("arrests", {"offense": "nonsense"}, "arrests"),
        ("property", {"offense": "XX"}, "property"),
        ("nibrs", {"offense": "ZZZ"}, "nibrs"),
    ],
)
def test_unknown_offense_is_422_without_upstream_call(
    client_for: Any, route: str, params: dict[str, str], kw: str
) -> None:
    fake = FakeCde()
    r = client_for(fake).get(f"/api/agency/{ORI}/{route}", params=params)
    assert r.status_code == 422
    assert fake.calls[kw] == 0


def test_arrest_offense_forms_share_one_key(client_for: Any) -> None:
    resp = ArrestTotalsResponse.model_validate(_sample("arrest_state_NY_all"))
    fake = FakeCde(arrests=resp)
    c = client_for(fake)
    for offense in ("homicide", "11"):
        assert c.get(f"/api/agency/{ORI}/arrests", params={"offense": offense}).status_code == 200
    assert fake.calls["arrests"] == 1


# -- cache --------------------------------------------------------------------
def test_categories_share_one_unfiltered_upstream_call(client_for: Any) -> None:
    fake = FakeCde(hate_crime=HateCrimeResponse.model_validate(_sample("hate_crime_agency")))
    c = client_for(fake)
    all_rows = c.get(f"/api/agency/{ORI}/hate-crime").json()
    cats = sorted({r["category"] for r in all_rows})
    assert len(cats) > 1
    for cat in cats:
        rows = c.get(f"/api/agency/{ORI}/hate-crime", params={"category": cat}).json()
        assert rows and {r["category"] for r in rows} == {cat}
    assert fake.calls["hate_crime"] == 1


def test_valid_empty_result_is_cached_briefly(client_for: Any) -> None:
    empty = HateCrimeResponse.model_validate({})
    fake = FakeCde(hate_crime=empty)
    c = client_for(fake)
    assert c.get(f"/api/agency/{ORI}/hate-crime").json() == []
    assert c.get(f"/api/agency/{ORI}/hate-crime").json() == []
    assert fake.calls["hate_crime"] == 1


def test_cache_ttl_and_lru_eviction() -> None:
    now = [0.0]
    cache = LiveCache(max_entries=2, ttl=10, empty_ttl=1, clock=lambda: now[0])
    calls: list[str] = []

    def producer(key: str, rows: list[dict[str, Any]]) -> Any:
        def p() -> list[dict[str, Any]]:
            calls.append(key)
            return rows

        return p

    cache.get("a", producer("a", [{"v": 1}]))
    cache.get("b", producer("b", []))
    cache.get("a", producer("a", [{"v": 1}]))  # hit, and "a" is now most recent
    now[0] = 2.0
    cache.get("b", producer("b", []))  # the empty result expired after 1 s
    cache.get("c", producer("c", [{"v": 3}]))  # evicts the least recent ("a")
    cache.get("a", producer("a", [{"v": 1}]))
    assert calls == ["a", "b", "b", "c", "a"]
    assert len(cache) == 2


def test_cached_rows_are_copies() -> None:
    cache = LiveCache()
    first = cache.get("k", lambda: [{"v": 1}])
    first[0]["v"] = 999
    assert cache.get("k", lambda: [])[0]["v"] == 1


def test_concurrent_misses_make_one_upstream_call() -> None:
    cache = LiveCache()
    calls = {"n": 0}
    gate = threading.Event()

    def slow() -> list[dict[str, Any]]:
        calls["n"] += 1
        gate.wait(2)
        return [{"v": 1}]

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(cache.get, "k", slow) for _ in range(8)]
        time.sleep(0.1)
        gate.set()
        results = [f.result(timeout=5) for f in futures]
    assert calls["n"] == 1
    assert all(r == [{"v": 1}] for r in results)


def test_concurrent_misses_share_the_error_and_do_not_cache_it() -> None:
    cache = LiveCache()
    calls = {"n": 0}
    gate = threading.Event()

    def failing() -> list[dict[str, Any]]:
        calls["n"] += 1
        gate.wait(2)
        raise RuntimeError("upstream down")

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(cache.get, "k", failing) for _ in range(4)]
        time.sleep(0.1)
        gate.set()
        errors = [f.exception(timeout=5) for f in futures]
    assert calls["n"] == 1
    assert all(isinstance(e, RuntimeError) for e in errors)
    assert len(cache) == 0


# -- limits -------------------------------------------------------------------
def test_per_client_limit_is_429_with_retry_after(
    client_for: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        agency_live, "guard", LiveGuard(client_per_min=2, global_per_hour=1000, concurrency=4)
    )
    fake = FakeCde(summarized=_summarized())
    c = client_for(fake)
    codes = [
        c.get(f"/api/agency/{ORI}/offenses", params={"offense": o}).status_code
        for o in ("homicide", "rape", "robbery")
    ]
    assert codes == [200, 200, 429]
    r = c.get(f"/api/agency/{ORI}/offenses", params={"offense": "arson"})
    assert r.json()["code"] == "rate_limited"
    assert int(r.headers["retry-after"]) >= 1
    # A cache hit costs nothing, even when the client is over its limit.
    assert c.get(f"/api/agency/{ORI}/offenses", params={"offense": "homicide"}).status_code == 200


def test_clients_have_separate_buckets(client_for: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        agency_live, "guard", LiveGuard(client_per_min=1, global_per_hour=1000, concurrency=4)
    )
    fake = FakeCde(summarized=_summarized())
    c = client_for(fake)

    def get(offense: str, ip: str) -> int:
        r = c.get(
            f"/api/agency/{ORI}/offenses",
            params={"offense": offense},
            headers={"X-Forwarded-For": f"203.0.113.9, {ip}"},
        )
        return r.status_code

    assert get("homicide", "198.51.100.1") == 200
    assert get("rape", "198.51.100.1") == 429
    assert get("rape", "198.51.100.2") == 200


def test_global_budget_is_503(client_for: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        agency_live, "guard", LiveGuard(client_per_min=100, global_per_hour=1, concurrency=4)
    )
    fake = FakeCde(summarized=_summarized())
    c = client_for(fake)
    assert c.get(f"/api/agency/{ORI}/offenses", params={"offense": "homicide"}).status_code == 200
    r = c.get(f"/api/agency/{ORI}/offenses", params={"offense": "rape"})
    assert r.status_code == 503
    assert r.json()["code"] == "live_budget_spent"
    assert "retry-after" in r.headers


def test_upstream_slots_cap_concurrency() -> None:
    g = LiveGuard(client_per_min=100, global_per_hour=1000, concurrency=2, slot_wait=0.05)
    with (
        g.upstream_slot(),
        g.upstream_slot(),
        pytest.raises(LiveLimitError) as info,
        g.upstream_slot(),
    ):
        pass
    assert info.value.status == 503
    with g.upstream_slot():  # slots are released
        pass


def test_token_bucket_refills() -> None:
    now = [0.0]
    g = LiveGuard(client_per_min=60, global_per_hour=3600, concurrency=1, clock=lambda: now[0])
    for _ in range(60):
        g.admit("x")
    with pytest.raises(LiveLimitError):
        g.admit("x")
    now[0] = 1.0  # one token per second
    g.admit("x")
