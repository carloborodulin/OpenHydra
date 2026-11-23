"""Request IDs, one JSON log line per request, and upstream error responses.

The live agency routes call the FBI CDE API. When that call fails, the API
returns an error status with a stable code. An empty list (200 []) means only
that the upstream answer was valid and empty.

| Upstream failure                         | Status | code                    |
|------------------------------------------|--------|-------------------------|
| No API key on this server                | 503    | live_data_unconfigured  |
| The key is rejected (401/403)            | 503    | upstream_auth           |
| Rate limit spent (429)                   | 503    | upstream_rate_limited   |
| Timeout                                  | 504    | upstream_timeout        |
| 404, 5xx, other 4xx, connection failure  | 502    | upstream_error          |
| Body is not JSON or has a bad shape      | 502    | upstream_bad_response   |
"""

from __future__ import annotations

import json
import logging
import math
import re
import sys
import time
import uuid
from contextvars import ContextVar
from typing import Any

import duckdb
from cdeclient import (
    CdeAuthError,
    CdeConfigError,
    CdeDecodeError,
    CdeError,
    CdeHttpError,
    CdeRateLimited,
    CdeTimeout,
    CdeTransportError,
    redact,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .live_guard import LiveLimitError

log = logging.getLogger("openhydra.access")

# Per-request facts that handlers deep in the stack fill in. The dict is
# mutable on purpose: sync routes run in a worker thread with a copy of the
# context, so a new value set there would not reach the middleware, but a
# change to this shared dict does.
_request: ContextVar[dict[str, Any] | None] = ContextVar("openhydra_request", default=None)

_SAFE_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_ID_HEADERS = (b"x-railway-request-id", b"x-request-id")


def note(**facts: Any) -> None:
    """Record facts (for example cache="hit") for the current request log line."""
    state = _request.get()
    if state is not None:
        state.update(facts)


def client_id() -> str:
    """The client address for rate limits ("unknown" outside a request)."""
    state = _request.get()
    return "unknown" if state is None else str(state.get("client", "unknown"))


def _client_address(scope: Scope, headers: dict[bytes, bytes]) -> str:
    # The Railway edge appends the address it sees to X-Forwarded-For. A client
    # can forge the entries before it, so use the last entry only.
    forwarded = headers.get(b"x-forwarded-for", b"").decode("latin-1")
    last = forwarded.split(",")[-1].strip()
    if last:
        return last[:64]
    peer = scope.get("client")
    return str(peer[0]) if peer else "unknown"


def current_request_id() -> str | None:
    state = _request.get()
    return None if state is None else state.get("request_id")


def configure_logging() -> None:
    """Write the access log as JSON lines on stdout (idempotent)."""
    if any(getattr(h, "_openhydra", False) for h in log.handlers):
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler._openhydra = True  # type: ignore[attr-defined]
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False


class RequestContextMiddleware:
    """Set X-Request-ID on each response and write one JSON log line."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        rid = None
        for name in _ID_HEADERS:
            raw = headers.get(name, b"").decode("latin-1")
            if _SAFE_ID.match(raw):
                rid = raw
                break
        state: dict[str, Any] = {
            "request_id": rid or uuid.uuid4().hex,
            "client": _client_address(scope, headers),
        }
        token = _request.set(state)
        start = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", [])
                message["headers"].append((b"x-request-id", state["request_id"].encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            record = {
                "request_id": state["request_id"],
                "method": scope.get("method"),
                "route": _route_template(scope),
                "status": status,
                "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                "cache": state.get("cache"),
                "upstream": state.get("upstream"),
            }
            log.info(redact(json.dumps(record, separators=(",", ":"))))
            _request.reset(token)


def _route_template(scope: Scope) -> str:
    """The route template with the prefix the client used (/api/v1 or /api)."""
    found = getattr(scope.get("route"), "path", None)
    if not isinstance(found, str):
        return "(static)"
    route: str = found
    path: str = scope.get("path", "")
    for prefix in ("/api/v1", "/api"):
        if path.startswith(prefix + "/") and not route.startswith(prefix + "/"):
            return prefix + route
    return route


def _error(
    request: Request, status: int, code: str, detail: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"detail": detail, "code": code, "request_id": current_request_id()},
        headers={"Cache-Control": "no-store", **(headers or {})},
    )


def upstream_class(exc: Exception) -> str:
    """A short label for the access log: the kind of upstream failure."""
    if isinstance(exc, CdeTimeout):
        return "timeout"
    if isinstance(exc, CdeRateLimited):
        return "429"
    if isinstance(exc, CdeHttpError):
        return f"{exc.status_code // 100}xx"
    if isinstance(exc, CdeTransportError):
        return "transport"
    if isinstance(exc, CdeDecodeError | ValidationError):
        return "bad_body"
    if isinstance(exc, CdeConfigError):
        return "unconfigured"
    return "error"


async def handle_cde_error(request: Request, exc: Exception) -> JSONResponse:
    note(upstream=upstream_class(exc))
    if isinstance(exc, CdeConfigError):
        return _error(request, 503, "live_data_unconfigured", "Live agency data is not configured.")
    if isinstance(exc, CdeAuthError):
        return _error(request, 503, "upstream_auth", "The FBI data service rejected this server.")
    if isinstance(exc, CdeRateLimited):
        wait = exc.retry_after if exc.retry_after is not None else 60.0
        return _error(
            request,
            503,
            "upstream_rate_limited",
            "The FBI data service rate limit is spent. Try again later.",
            {"Retry-After": str(math.ceil(wait))},
        )
    if isinstance(exc, CdeTimeout):
        return _error(request, 504, "upstream_timeout", "The FBI data service did not answer.")
    if isinstance(exc, CdeDecodeError | ValidationError):
        return _error(
            request, 502, "upstream_bad_response", "The FBI data service sent an unexpected answer."
        )
    return _error(request, 502, "upstream_error", "The FBI data service failed.")


async def handle_live_limit(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, LiveLimitError)
    note(upstream="refused")
    return _error(request, exc.status, exc.code, exc.detail, {"Retry-After": str(exc.retry_after)})


async def handle_warehouse_error(request: Request, exc: Exception) -> JSONResponse:
    # The message can hold a file path, so it stays in the log only.
    log.warning(json.dumps({"request_id": current_request_id(), "warehouse_error": str(exc)}))
    return _error(request, 503, "warehouse_unavailable", "The data warehouse is not available.")


def install(app: FastAPI) -> None:
    configure_logging()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(CdeError, handle_cde_error)
    app.add_exception_handler(ValidationError, handle_cde_error)
    app.add_exception_handler(LiveLimitError, handle_live_limit)
    app.add_exception_handler(duckdb.Error, handle_warehouse_error)
