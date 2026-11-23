"""CDE API client access for live agency drill-down (FastAPI dependency).

The client reads ``FBI_CDE_API_KEY`` from the environment. In production that
must be set in the runtime env (Railway), since these routes, unlike the
warehouse routes, call the FBI gateway live.

The routes get a *provider*, not a client. They call it only on a cache miss,
so a cache hit does no client work at all. The provider returns one shared
client: an httpx connection pool is safe to share across the worker threads.
It uses the INTERACTIVE retry policy (short total deadline), so a slow
upstream cannot hold a worker thread for minutes.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from cdeclient import INTERACTIVE, CdeClient

ClientProvider = Callable[[], CdeClient]

_lock = threading.Lock()
_shared: CdeClient | None = None


def shared_client() -> CdeClient:
    """Return the shared client. Raises CdeConfigError when no key is set."""
    global _shared
    with _lock:
        if _shared is None:
            _shared = CdeClient(policy=INTERACTIVE)
        return _shared


def close_shared_client() -> None:
    global _shared
    with _lock:
        if _shared is not None:
            _shared.close()
            _shared = None


def get_cde_client() -> ClientProvider:
    return shared_client
