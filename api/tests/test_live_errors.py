"""Upstream failures map to stable error statuses on all seven live routes."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest
from cdeclient import (
    CdeAuthError,
    CdeConfigError,
    CdeDecodeError,
    CdeError,
    CdeNotFound,
    CdeRateLimited,
    CdeTimeout,
    CdeTransportError,
    CdeUpstreamError,
)
from cdeclient.models import ChartResponse, SummarizedResponse
from fastapi.testclient import TestClient
from pydantic import ValidationError

from openhydra_api import agency_live, cde
from openhydra_api.main import app

from .test_agency_live import FakeCde, _sample

ORI = "NY0303000"
# (route, FakeCde keyword, params)
ROUTES = [
    (f"/api/agency/{ORI}/offenses", "summarized", {"offense": "homicide"}),
    (f"/api/agency/{ORI}/arrests", "arrests", {"offense": "homicide"}),
    (f"/api/agency/{ORI}/police-employment", "pe", {}),
    (f"/api/agency/{ORI}/hate-crime", "hate_crime", {}),
    (f"/api/agency/{ORI}/shr", "shr", {}),
    (f"/api/agency/{ORI}/property", "property_", {"offense": "NB"}),
    (f"/api/agency/{ORI}/nibrs", "nibrs", {"offense": "13A"}),
]


def _validation_error() -> ValidationError:
    try:
        SummarizedResponse.model_validate({"offenses": "bad"})
    except ValidationError as exc:
        return exc
    raise AssertionError("expected a ValidationError")


FAILURES: list[tuple[str, CdeError | ValidationError, int, str]] = [
    ("missing key", CdeConfigError("No API key."), 503, "live_data_unconfigured"),
    ("401", CdeAuthError(401, "p"), 503, "upstream_auth"),
    ("403", CdeAuthError(403, "p"), 503, "upstream_auth"),
    ("404", CdeNotFound(404, "p"), 502, "upstream_error"),
    ("429", CdeRateLimited("p", retry_after=30), 503, "upstream_rate_limited"),
    ("500", CdeUpstreamError(500, "p"), 502, "upstream_error"),
    ("timeout", CdeTimeout("p"), 504, "upstream_timeout"),
    ("transport", CdeTransportError("p", "ConnectError", retryable=True), 502, "upstream_error"),
    ("bad json", CdeDecodeError("p", "the body is not JSON"), 502, "upstream_bad_response"),
    ("bad shape", _validation_error(), 502, "upstream_bad_response"),
]


@pytest.fixture
def client_for(live_db):
    def _make(fake: FakeCde) -> TestClient:
        agency_live.clear_cache()
        app.dependency_overrides[cde.get_cde_client] = lambda: lambda: fake
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()
    agency_live.clear_cache()


@pytest.mark.parametrize(("route", "kw", "params"), ROUTES, ids=[r[1] for r in ROUTES])
@pytest.mark.parametrize(
    ("name", "error", "status", "code"), FAILURES, ids=[f[0] for f in FAILURES]
)
def test_upstream_failure_is_an_error_status(
    client_for: Any,
    route: str,
    kw: str,
    params: dict[str, str],
    name: str,
    error: Exception,
    status: int,
    code: str,
) -> None:
    fake = FakeCde(**{kw: error})
    c = client_for(fake)
    r = c.get(route, params=params)
    assert r.status_code == status
    body = r.json()
    assert body["code"] == code
    assert body["request_id"] == r.headers["x-request-id"]
    assert r.headers["cache-control"] == "no-store"
    if name == "429":
        assert r.headers["retry-after"] == "30"
    # Errors are never cached: a second request calls upstream again.
    c.get(route, params=params)
    calls_key = "property" if kw == "property_" else kw
    assert fake.calls[calls_key] == 2


def test_sparse_valid_response_is_200_with_rows(client_for: Any) -> None:
    fake = FakeCde(pe=ChartResponse.model_validate(_sample("pe_state_NY")))
    r = client_for(fake).get(f"/api/agency/{ORI}/police-employment")
    assert r.status_code == 200
    assert r.json()


def test_cache_hit_does_not_touch_the_client(client_for: Any) -> None:  # noqa: ARG001
    built = {"n": 0}
    fake = FakeCde(
        summarized=SummarizedResponse.model_validate(_sample("summarized_agency_violent"))
    )

    def provider() -> Any:
        built["n"] += 1
        return fake

    agency_live.clear_cache()
    app.dependency_overrides[cde.get_cde_client] = lambda: provider
    c = TestClient(app)
    for _ in range(3):
        assert (
            c.get(f"/api/agency/{ORI}/offenses", params={"offense": "homicide"}).status_code == 200
        )
    assert built["n"] == 1


def test_access_log_line(client_for: Any, caplog: pytest.LogCaptureFixture) -> None:
    fake = FakeCde(summarized=CdeTimeout("p"))
    c = client_for(fake)
    logger = logging.getLogger("openhydra.access")
    logger.propagate = True  # let caplog see the record
    try:
        with caplog.at_level(logging.INFO, logger="openhydra.access"):
            r = c.get(
                f"/api/agency/{ORI}/offenses",
                params={"offense": "homicide"},
                headers={"X-Request-ID": "abc-123"},
            )
    finally:
        logger.propagate = False
    assert r.headers["x-request-id"] == "abc-123"
    lines = [
        json.loads(rec.getMessage()) for rec in caplog.records if rec.name == "openhydra.access"
    ]
    line = lines[-1]
    assert line["request_id"] == "abc-123"
    assert line["route"] == "/api/agency/{ori}/offenses"
    assert line["status"] == 504
    assert line["cache"] == "miss"
    assert line["upstream"] == "timeout"


def test_unsafe_request_id_is_replaced(client_for: Any) -> None:
    c = client_for(FakeCde(summarized=CdeTimeout("p")))
    r = c.get(
        f"/api/agency/{ORI}/offenses",
        params={"offense": "homicide"},
        headers={"X-Request-ID": "bad id\twith tab"},
    )
    assert r.headers["x-request-id"] != "bad id\twith tab"
    assert len(r.headers["x-request-id"]) == 32
