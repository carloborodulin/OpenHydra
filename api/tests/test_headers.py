"""INFRA-3 and PERF-3: cache policy, ETags, security headers, compact agency points."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from openhydra_api import main


@pytest.fixture
def release(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr(main, "current_release", lambda: "R1")
    return "R1"


def test_security_headers_on_every_response(client: TestClient) -> None:
    r = client.get("/api/meta")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "geolocation=()" in r.headers["permissions-policy"]
    assert r.headers["strict-transport-security"].startswith("max-age=")
    csp = r.headers["content-security-policy"]
    assert "script-src 'self'" in csp and "'unsafe-eval'" not in csp
    assert "frame-ancestors 'none'" in csp


def test_docs_page_keeps_its_cdn_scripts(client: TestClient) -> None:
    assert "content-security-policy" not in client.get("/docs").headers


def test_warehouse_get_has_etag_and_304(client: TestClient, release: str) -> None:
    r = client.get("/api/meta")
    assert r.headers["cache-control"] == "public, max-age=300"
    etag = r.headers["etag"]
    assert etag.startswith('W/"R1-')
    again = client.get("/api/meta", headers={"If-None-Match": etag})
    assert again.status_code == 304
    assert again.content == b""
    # Another URL has another tag.
    assert client.get("/api/population").headers["etag"] != etag


def test_live_and_health_are_not_cached(client: TestClient, release: str) -> None:
    assert client.get("/health").headers["cache-control"] == "no-store"
    r = client.get("/api/agency/ZZ9999999/offenses", params={"offense": "homicide"})
    assert r.headers["cache-control"] == "no-store"
    assert "etag" not in r.headers


def test_errors_are_not_cached(client: TestClient, release: str) -> None:
    r = client.get("/api/offenses/monthly", params={"offense": "nope"})
    assert r.status_code == 404
    assert r.headers["cache-control"] == "no-store"


def test_points_are_compact_and_immutable_for_the_release(client: TestClient, release: str) -> None:
    r = client.get("/api/agencies/points", params={"v": "R1"})
    body = r.json()
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert body["release_id"] == "R1"
    assert body["ori"] == ["NY001"]
    assert body["lat"] == [42.0] and body["nibrs"] == [True]
    assert len({len(body[k]) for k in ("ori", "name", "county", "lat", "lon", "nibrs")}) == 1
    # A stale version gets the short policy, so it cannot pin old data.
    stale = client.get("/api/agencies/points", params={"v": "R0"})
    assert stale.headers["cache-control"] == "public, max-age=300"


def test_agency_detail(client: TestClient) -> None:
    assert client.get("/api/agencies/NY0303000").status_code == 404
    assert client.get("/api/agencies/bad").status_code == 422


def test_v1_is_the_documented_api_and_old_paths_are_aliases(client: TestClient) -> None:
    v1 = client.get("/api/v1/meta")
    old = client.get("/api/meta")
    assert v1.status_code == old.status_code == 200
    assert v1.json() == old.json()
    assert "deprecation" not in v1.headers
    assert old.headers["deprecation"] == "true"
    assert old.headers["link"] == '</api/v1/meta>; rel="successor-version"'
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/meta" in paths and "/api/meta" not in paths


def test_v1_live_routes_keep_their_cache_policy(client: TestClient) -> None:
    r = client.get("/api/v1/agency/ZZ9999999/offenses", params={"offense": "homicide"})
    assert r.headers["cache-control"] == "no-store"
