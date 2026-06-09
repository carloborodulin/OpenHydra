"""CDE API client access for live agency drill-down (FastAPI dependency).

The client reads ``FBI_CDE_API_KEY`` from the environment. In production that
must be set in the runtime env (Railway), since these routes — unlike the
warehouse routes — call the FBI gateway live. A fresh client per request is
cheap (caching keeps live calls rare) and avoids sharing one httpx client across
the threadpool.
"""

from __future__ import annotations

from collections.abc import Iterator

from cdeclient import CdeClient, CdeError
from fastapi import HTTPException


def get_cde_client() -> Iterator[CdeClient]:
    try:
        client = CdeClient()
    except CdeError as exc:
        raise HTTPException(
            status_code=503, detail="CDE API key not configured for live agency data"
        ) from exc
    try:
        yield client
    finally:
        client.close()
