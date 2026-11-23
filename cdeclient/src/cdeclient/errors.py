"""Typed errors for the CDE client.

No error message contains a request URL. The API key travels in the query
string, so a URL in a message, a log line or a traceback would disclose it.
Each error carries the HTTP status (when there is one) and the relative path.
"""

from __future__ import annotations


class CdeError(RuntimeError):
    """Base error for the CDE client."""

    #: True when a new attempt can succeed (rate limit, gateway error, timeout).
    retryable: bool = False


class CdeConfigError(CdeError):
    """The client has no API key or no usable configuration."""


class CdeHttpError(CdeError):
    """The CDE API returned a status that is not a success."""

    def __init__(self, status_code: int, path: str, detail: str | None = None) -> None:
        msg = f"CDE API returned status {status_code} for {path}"
        super().__init__(f"{msg}: {detail}" if detail else msg)
        self.status_code = status_code
        self.path = path


class CdeAuthError(CdeHttpError):
    """The CDE API rejected the API key (401 or 403)."""


class CdeNotFound(CdeHttpError):
    """The CDE API has no resource at this path (404)."""


class CdeRateLimited(CdeHttpError):
    """The CDE API rate limit is spent (429)."""

    retryable = True

    def __init__(self, path: str, retry_after: float | None = None) -> None:
        super().__init__(429, path)
        self.retry_after = retry_after


class CdeUpstreamError(CdeHttpError):
    """The CDE API failed on its side (5xx) or sent an unexpected 4xx."""

    def __init__(self, status_code: int, path: str, detail: str | None = None) -> None:
        super().__init__(status_code, path, detail)
        self.retryable = status_code in {500, 502, 503, 504}


# Old name, kept so that callers written for version 0.1 still import.
CdeServerError = CdeUpstreamError


class CdeTimeout(CdeError):
    """The CDE API did not answer in time."""

    retryable = True

    def __init__(self, path: str) -> None:
        super().__init__(f"CDE API timed out for {path}")
        self.path = path


class CdeTransportError(CdeError):
    """The connection to the CDE API failed."""

    def __init__(self, path: str, kind: str, *, retryable: bool) -> None:
        super().__init__(f"CDE API connection failed for {path} ({kind})")
        self.path = path
        self.retryable = retryable


class CdeDecodeError(CdeError):
    """The CDE API sent a body that is not valid JSON or has an unexpected shape."""

    def __init__(self, path: str, detail: str) -> None:
        super().__init__(f"CDE API sent an unexpected body for {path}: {detail}")
        self.path = path
