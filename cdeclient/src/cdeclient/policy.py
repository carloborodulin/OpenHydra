"""Retry policies and log redaction for CDE requests."""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass

import httpx
from tenacity import RetryCallState

from .errors import CdeRateLimited


@dataclass(frozen=True)
class RetryPolicy:
    """How long and how often the client tries one request.

    Attributes:
        max_attempts: the maximum number of attempts, including the first.
        base_wait: the first backoff step in seconds. Later steps double.
        max_wait: the largest single wait in seconds. A Retry-After value is
            clipped to this limit too.
        deadline: the total time budget in seconds for all attempts, or None.
        connect_timeout / read_timeout: the httpx timeouts for one attempt.
    """

    max_attempts: int = 6
    base_wait: float = 0.5
    max_wait: float = 10.0
    deadline: float | None = None
    connect_timeout: float = 10.0
    read_timeout: float = 30.0

    def timeout(self) -> httpx.Timeout:
        return httpx.Timeout(self.read_timeout, connect=self.connect_timeout)

    def wait(self, state: RetryCallState) -> float:
        """Honor a bounded Retry-After, else use full-jitter exponential backoff."""
        exc = state.outcome.exception() if state.outcome else None
        if isinstance(exc, CdeRateLimited) and exc.retry_after is not None:
            return max(0.0, min(exc.retry_after, self.max_wait))
        ceiling = min(self.max_wait, self.base_wait * 2 ** (state.attempt_number - 1))
        return random.uniform(0, ceiling)


#: For a web request that waits on the answer: fail fast, keep the worker free.
INTERACTIVE = RetryPolicy(
    max_attempts=2,
    base_wait=0.25,
    max_wait=2.0,
    deadline=8.0,
    connect_timeout=3.0,
    read_timeout=5.0,
)

#: For the bulk extract: patient, and it honors the rate limit of the API.
BULK = RetryPolicy(
    max_attempts=8,
    base_wait=1.0,
    max_wait=60.0,
    deadline=None,
    connect_timeout=10.0,
    read_timeout=60.0,
)


_KEY_IN_QUERY = re.compile(r"(?i)(api_key=)[^&\s\"'#]+")


def redact(text: str) -> str:
    """Replace the value of each ``API_KEY=`` query parameter with ``***``."""
    return _KEY_IN_QUERY.sub(r"\1***", text)


class RedactApiKeyFilter(logging.Filter):
    """Remove the API key from each log record (httpx logs full request URLs)."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        cleaned = redact(message)
        if cleaned != message:
            record.msg = cleaned
            record.args = None
        return True


_FILTER = RedactApiKeyFilter()


def install_log_redaction() -> None:
    """Attach the redaction filter to the httpx and httpcore loggers (idempotent)."""
    names = ("httpx", "httpcore", "httpcore.http11", "httpcore.http2", "httpcore.connection")
    for name in names:
        logger = logging.getLogger(name)
        if _FILTER not in logger.filters:
            logger.addFilter(_FILTER)
