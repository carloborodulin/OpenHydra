"""Failure modes of the client: typed errors, no key disclosure, retry policy."""

from __future__ import annotations

import logging
import traceback
from collections.abc import Callable
from typing import Any

import httpx
import pytest
import respx
from httpx import Response
from pydantic import SecretStr

from cdeclient import (
    BULK,
    INTERACTIVE,
    CdeAuthError,
    CdeClient,
    CdeConfigError,
    CdeDecodeError,
    CdeError,
    CdeNotFound,
    CdeRateLimited,
    CdeTimeout,
    CdeTransportError,
    CdeUpstreamError,
    RetryPolicy,
    Settings,
    redact,
)

BASE = "https://api.test/crime/fbi/cde"
SENTINEL = "SENTINEL-KEY-7f3a9c"
PATH = f"{BASE}/summarized/agency/NY0303000/homicide"


def _client(waits: list[float] | None = None, policy: RetryPolicy | None = None) -> CdeClient:
    return CdeClient(
        api_key=SENTINEL,
        base_url=BASE,
        policy=policy or RetryPolicy(max_attempts=3, base_wait=0, max_wait=0),
        sleep=(waits.append if waits is not None else (lambda _: None)),
    )


def _call(c: CdeClient) -> object:
    return c.summarized_agency("NY0303000", "homicide", "01-2024", "12-2024")


def _assert_no_key(exc: BaseException) -> None:
    rendered = "".join(traceback.format_exception(exc))
    assert SENTINEL not in rendered
    assert SENTINEL not in repr(exc)
    # No httpx exception (which holds the URL) may be reachable from the error.
    assert exc.__cause__ is None
    assert exc.__context__ is None or exc.__suppress_context__


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (400, CdeUpstreamError),
        (401, CdeAuthError),
        (403, CdeAuthError),
        (404, CdeNotFound),
        (429, CdeRateLimited),
        (500, CdeUpstreamError),
        (503, CdeUpstreamError),
    ],
)
@respx.mock
def test_status_maps_to_typed_error_without_key(status: int, error: type[CdeError]) -> None:
    respx.get(PATH).mock(return_value=Response(status))
    with _client() as c, pytest.raises(error) as info:
        _call(c)
    assert info.value.status_code == status  # type: ignore[attr-defined]
    assert "summarized/agency/NY0303000/homicide" in str(info.value)
    _assert_no_key(info.value)


@respx.mock
def test_timeout_maps_to_cde_timeout_after_retries() -> None:
    route = respx.get(PATH).mock(side_effect=httpx.ReadTimeout("read timed out"))
    with _client() as c, pytest.raises(CdeTimeout) as info:
        _call(c)
    assert route.call_count == 3
    _assert_no_key(info.value)


@respx.mock
def test_connect_error_retries_then_maps_to_transport_error() -> None:
    route = respx.get(PATH).mock(side_effect=httpx.ConnectError("refused"))
    with _client() as c, pytest.raises(CdeTransportError) as info:
        _call(c)
    assert route.call_count == 3
    assert info.value.retryable
    _assert_no_key(info.value)


@respx.mock
def test_non_retryable_transport_error_fails_at_once() -> None:
    route = respx.get(PATH).mock(side_effect=httpx.UnsupportedProtocol("bad scheme"))
    with _client() as c, pytest.raises(CdeTransportError):
        _call(c)
    assert route.call_count == 1


@respx.mock
def test_invalid_json_maps_to_decode_error() -> None:
    respx.get(PATH).mock(return_value=Response(200, text="<html>gateway</html>"))
    with _client() as c, pytest.raises(CdeDecodeError) as info:
        _call(c)
    _assert_no_key(info.value)


@respx.mock
def test_unexpected_shape_maps_to_decode_error() -> None:
    respx.get(PATH).mock(return_value=Response(200, json={"offenses": "not-a-mapping"}))
    with _client() as c, pytest.raises(CdeDecodeError):
        _call(c)


@respx.mock
def test_4xx_other_than_429_is_not_retried() -> None:
    route = respx.get(PATH).mock(return_value=Response(404))
    with _client() as c, pytest.raises(CdeNotFound):
        _call(c)
    assert route.call_count == 1


@respx.mock
def test_retry_after_is_honored_and_bounded(sample: Callable[[str], Any]) -> None:
    waits: list[float] = []
    respx.get(PATH).mock(
        side_effect=[
            Response(429, headers={"Retry-After": "3"}),
            Response(429, headers={"Retry-After": "999"}),
            Response(200, json=sample("summarized_agency_violent")),
        ]
    )
    policy = RetryPolicy(max_attempts=3, base_wait=0.1, max_wait=5.0)
    with _client(waits, policy) as c:
        _call(c)
    assert waits == [3.0, 5.0]


@respx.mock
def test_backoff_has_jitter_within_the_ceiling(sample: Callable[[str], Any]) -> None:
    waits: list[float] = []
    respx.get(PATH).mock(
        side_effect=[
            Response(503),
            Response(503),
            Response(200, json=sample("summarized_agency_violent")),
        ]
    )
    policy = RetryPolicy(max_attempts=3, base_wait=1.0, max_wait=10.0)
    with _client(waits, policy) as c:
        _call(c)
    assert len(waits) == 2
    assert 0 <= waits[0] <= 1.0
    assert 0 <= waits[1] <= 2.0


def test_presets() -> None:
    assert INTERACTIVE.max_attempts == 2
    assert INTERACTIVE.deadline is not None and INTERACTIVE.deadline <= 10
    assert INTERACTIVE.read_timeout < BULK.read_timeout
    assert BULK.max_attempts == 8


@respx.mock
def test_httpx_request_log_is_redacted(
    caplog: pytest.LogCaptureFixture, sample: Callable[[str], Any]
) -> None:
    respx.get(PATH).mock(return_value=Response(200, json=sample("summarized_agency_violent")))
    with caplog.at_level(logging.DEBUG):
        # respx bypasses the real transport, so log a request line the way httpx does.
        logging.getLogger("httpx").info(
            'HTTP Request: %s %s "%s %d %s"',
            "GET",
            f"{PATH}?from=01-2024&API_KEY={SENTINEL}",
            "HTTP/1.1",
            200,
            "OK",
        )
        with _client() as c:
            _call(c)
    assert caplog.records
    assert SENTINEL not in caplog.text
    assert "API_KEY=***" in caplog.text


def test_redact_handles_several_forms() -> None:
    text = f"a?API_KEY={SENTINEL}&b=1 api_key={SENTINEL} x"
    assert SENTINEL not in redact(text)


def test_key_is_secret_in_settings_and_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FBI_CDE_API_KEY", SENTINEL)
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert isinstance(s.api_key, SecretStr)
    assert SENTINEL not in repr(s)
    c = CdeClient(settings=s, base_url=BASE)
    assert SENTINEL not in repr(c)
    assert SENTINEL not in str(vars(c))
    c.close()


def test_missing_key_is_config_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FBI_CDE_API_KEY", raising=False)
    with pytest.raises(CdeConfigError):
        CdeClient(settings=Settings(_env_file=None), base_url=BASE)  # type: ignore[call-arg]
