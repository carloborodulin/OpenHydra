"""Browser security headers and cache policy for every response (INFRA-3).

Cache policy, by path:

| Response                                      | Cache-Control                          |
|-----------------------------------------------|----------------------------------------|
| /assets/* (content-hashed by Vite)            | public, max-age=31536000, immutable    |
| /api/agencies/points?v=<current release>      | public, max-age=31536000, immutable    |
| Other warehouse GET /api/* (200)              | public, max-age=300, plus an ETag      |
| Live agency routes, /health, errors           | no-store                               |
| HTML and other static files                   | no-cache (revalidate each time)        |

The ETag of a warehouse route is the release ID plus the request URL, so it
changes with each data release. A matching If-None-Match gets a 304 without
a query.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from starlette.types import ASGIApp, Message, Receive, Scope, Send

IMMUTABLE = "public, max-age=31536000, immutable"
SHORT = "public, max-age=300"

# Every script is a same-origin file (no inline script). Recharts and MapLibre
# set inline style attributes, so style-src needs 'unsafe-inline'. The basemap
# style, tiles, sprites and glyphs come from CARTO; the fonts from Google.
CSP = "; ".join(
    [
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
        "font-src 'self' https://fonts.gstatic.com",
        "img-src 'self' data: blob: https://*.cartocdn.com",
        # Chart PNG export makes the browser fetch the font stylesheet.
        "connect-src 'self' https://*.cartocdn.com https://fonts.googleapis.com",
        "worker-src 'self' blob:",
        "child-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "upgrade-insecure-requests",
    ]
)

SECURITY: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (
        b"permissions-policy",
        b"camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
    ),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"cross-origin-opener-policy", b"same-origin"),
]

# FastAPI's own docs pages load Swagger UI and ReDoc from a CDN with inline
# scripts, so they do not get the strict CSP.
NO_CSP_PREFIXES = ("/docs", "/redoc")


def _cache_policy(path: str, query: str, status: int, release: str | None) -> str:
    if status != 200 and status != 304:
        return "no-store"
    if path.startswith("/assets/"):
        return IMMUTABLE
    if path in ("/health",) or path.startswith("/api/agency/"):
        return "no-store"
    if path == "/api/agencies/points" and release and f"v={release}" in query.split("&"):
        return IMMUTABLE
    if path.startswith("/api/") or path == "/openapi.json":
        return SHORT
    return "no-cache"


def etag_for(release: str, path: str, query: str) -> str:
    digest = hashlib.sha256(f"{path}?{query}".encode()).hexdigest()[:16]
    return f'W/"{release}-{digest}"'


class SecurityAndCacheMiddleware:
    """Add the security headers and the cache policy; answer 304 for a known ETag."""

    def __init__(self, app: ASGIApp, release: Callable[[], str | None]) -> None:
        self.app = app
        self.release = release

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path: str = scope.get("path", "")
        query = scope.get("query_string", b"").decode("latin-1")
        warehouse_api = (
            scope.get("method") == "GET"
            and path.startswith("/api/")
            and not path.startswith("/api/agency/")
        )
        release = self.release() if warehouse_api else None
        etag = etag_for(release, path, query) if release else None

        if etag is not None:
            sent = dict(scope.get("headers") or []).get(b"if-none-match", b"").decode("latin-1")
            if etag in [t.strip() for t in sent.split(",")]:
                headers = [
                    (b"etag", etag.encode()),
                    (b"cache-control", _cache_policy(path, query, 304, release).encode()),
                    *SECURITY,
                ]
                await send({"type": "http.response.start", "status": 304, "headers": headers})
                await send({"type": "http.response.body", "body": b""})
                return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                names = {k.lower() for k, _ in headers}
                if b"cache-control" not in names:
                    headers.append(
                        (b"cache-control", _cache_policy(path, query, status, release).encode())
                    )
                if etag is not None and status == 200:
                    headers.append((b"etag", etag.encode()))
                headers += [h for h in SECURITY if h[0] not in names]
                if not path.startswith(NO_CSP_PREFIXES) and b"content-security-policy" not in names:
                    headers.append((b"content-security-policy", CSP.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
