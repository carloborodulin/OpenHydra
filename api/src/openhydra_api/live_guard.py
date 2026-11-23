"""Limits on live upstream work: one CDE API key serves every visitor.

Only a cache miss costs upstream quota, so only a cache miss passes these
checks. A cache hit and a request that waits on another request's fetch are
free.

- A per-client token bucket stops one visitor from spending the key quota.
  It answers 429 with Retry-After.
- A global hourly budget stays below the key quota (api.data.gov allows
  about 1,000 requests per hour), so the scheduled extract and the site can
  share the key. It answers 503 with Retry-After.
- A semaphore caps the number of upstream calls at the same time, so slow
  upstream answers cannot take all worker threads. It answers 503.

Set the limits with environment variables:
OPENHYDRA_LIVE_CLIENT_PER_MIN (default 30), OPENHYDRA_LIVE_GLOBAL_PER_HOUR
(default 600) and OPENHYDRA_LIVE_CONCURRENCY (default 4).
"""

from __future__ import annotations

import math
import os
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager


class LiveLimitError(Exception):
    """A live request that the API refuses before it calls upstream."""

    def __init__(self, status: int, code: str, detail: str, retry_after: float) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.retry_after = max(1, math.ceil(retry_after))


class TokenBucket:
    """A classic token bucket. Not thread-safe; the guard holds a lock."""

    def __init__(self, capacity: float, per_second: float, now: float) -> None:
        self.capacity = capacity
        self.per_second = per_second
        self.tokens = capacity
        self.updated = now

    def take(self, now: float) -> float:
        """Take one token. Return 0 on success, else the seconds until one is free."""
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.per_second)
        self.updated = now
        if self.tokens >= 1:
            self.tokens -= 1
            return 0.0
        return (1 - self.tokens) / self.per_second


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


class LiveGuard:
    def __init__(
        self,
        *,
        client_per_min: int,
        global_per_hour: int,
        concurrency: int,
        slot_wait: float = 10.0,
        max_clients: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client_per_min = client_per_min
        self.global_per_hour = global_per_hour
        self.slot_wait = slot_wait
        self._clock = clock
        self._lock = threading.Lock()
        self._clients: OrderedDict[str, TokenBucket] = OrderedDict()
        self._max_clients = max_clients
        self._global = TokenBucket(global_per_hour, global_per_hour / 3600.0, clock())
        self._slots = threading.BoundedSemaphore(concurrency)

    @classmethod
    def from_env(cls) -> LiveGuard:
        return cls(
            client_per_min=_env_int("OPENHYDRA_LIVE_CLIENT_PER_MIN", 30),
            global_per_hour=_env_int("OPENHYDRA_LIVE_GLOBAL_PER_HOUR", 600),
            concurrency=_env_int("OPENHYDRA_LIVE_CONCURRENCY", 4),
        )

    def admit(self, client_id: str) -> None:
        """Charge one upstream call to the client and to the global budget."""
        with self._lock:
            now = self._clock()
            bucket = self._clients.get(client_id)
            if bucket is None:
                bucket = TokenBucket(self.client_per_min, self.client_per_min / 60.0, now)
                self._clients[client_id] = bucket
                if len(self._clients) > self._max_clients:
                    self._clients.popitem(last=False)
            else:
                self._clients.move_to_end(client_id)
            wait = bucket.take(now)
            if wait:
                raise LiveLimitError(
                    429,
                    "rate_limited",
                    "Too many live agency requests from this client. Try again later.",
                    wait,
                )
            wait = self._global.take(now)
            if wait:
                bucket.tokens = min(bucket.capacity, bucket.tokens + 1)  # refund
                raise LiveLimitError(
                    503,
                    "live_budget_spent",
                    "The hourly budget for live agency data is spent. Try again later.",
                    wait,
                )

    @contextmanager
    def upstream_slot(self) -> Iterator[None]:
        """Hold one of the concurrent upstream slots for the duration of a call."""
        if not self._slots.acquire(timeout=self.slot_wait):
            raise LiveLimitError(
                503, "live_busy", "Live agency data is busy. Try again in a moment.", 5
            )
        try:
            yield
        finally:
            self._slots.release()


guard = LiveGuard.from_env()
