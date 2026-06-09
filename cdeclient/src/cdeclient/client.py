"""The CDE API client: typed methods over the verified endpoint families."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx
from pydantic import TypeAdapter
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import Settings
from .constants import ArrestType, Offense
from .dates import to_month, to_year
from .models import (
    Agency,
    ArrestTotalsResponse,
    ChartResponse,
    SummarizedResponse,
)

# Statuses worth retrying: gateway hiccups (the API throws intermittent 503s)
# and rate limiting.
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})

_AGENCIES_ADAPTER: TypeAdapter[dict[str, list[Agency]]] = TypeAdapter(dict[str, list[Agency]])


class CdeError(RuntimeError):
    """Base error for the CDE client."""


class CdeServerError(CdeError):
    """A retryable server-side response (5xx / 429)."""

    def __init__(self, status_code: int) -> None:
        super().__init__(f"CDE API returned retryable status {status_code}")
        self.status_code = status_code


def _slug(offense: Offense | str) -> str:
    return offense.value if isinstance(offense, Offense) else str(offense)


def _arrest_type(value: ArrestType | str) -> str:
    return value.value if isinstance(value, ArrestType) else str(value)


class CdeClient:
    """A typed, retrying client for the FBI Crime Data Explorer API.

    Args:
        api_key: API key. Falls back to ``FBI_CDE_API_KEY`` (env / .env).
        base_url: API base URL. Falls back to ``FBI_CDE_BASE_URL`` or the default.
        max_attempts / base_wait / max_wait: retry/backoff tuning.
        sleep: sleep function (injectable so tests run instantly).
        transport: httpx transport (injectable for mocking).
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        settings: Settings | None = None,
        timeout: float = 30.0,
        max_attempts: int = 6,
        base_wait: float = 0.5,
        max_wait: float = 10.0,
        sleep: Callable[[float], Any] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        settings = settings or Settings()
        key = api_key or settings.api_key
        if not key:
            raise CdeError(
                "No API key. Pass api_key=... or set FBI_CDE_API_KEY in the "
                "environment / .env file."
            )
        self.api_key: str = key
        # Trailing slash + relative paths so httpx preserves the base path.
        base = (base_url or settings.base_url).rstrip("/") + "/"
        self._client = httpx.Client(base_url=base, timeout=timeout, transport=transport)
        self._retrying = Retrying(
            reraise=True,
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=base_wait, max=max_wait),
            retry=retry_if_exception_type((CdeServerError, httpx.TransportError)),
            sleep=sleep,
        )

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CdeClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- low level ---------------------------------------------------------
    def _get_json(self, path: str, params: dict[str, str] | None = None) -> Any:
        query: dict[str, str] = {**(params or {}), "API_KEY": self.api_key}

        def _do() -> Any:
            resp = self._client.get(path, params=query)
            if resp.status_code in RETRY_STATUS:
                raise CdeServerError(resp.status_code)
            resp.raise_for_status()
            return resp.json()

        return self._retrying(_do)

    @staticmethod
    def _range(from_: str | date, to: str | date, *, yearly: bool = False) -> dict[str, str]:
        if yearly:
            return {"from": to_year(from_), "to": to_year(to)}
        return {"from": to_month(from_), "to": to_month(to)}

    # -- agencies ----------------------------------------------------------
    def agencies_by_state(self, state: str) -> dict[str, list[Agency]]:
        """Agencies in a state, grouped by county."""
        data = self._get_json(f"agency/byStateAbbr/{state.upper()}")
        return _AGENCIES_ADAPTER.validate_python(data)

    # -- summarized --------------------------------------------------------
    def summarized_national(
        self, offense: Offense | str, from_: str | date, to: str | date
    ) -> SummarizedResponse:
        data = self._get_json(f"summarized/national/{_slug(offense)}", self._range(from_, to))
        return SummarizedResponse.model_validate(data)

    def summarized_state(
        self, state: str, offense: Offense | str, from_: str | date, to: str | date
    ) -> SummarizedResponse:
        data = self._get_json(
            f"summarized/state/{state.upper()}/{_slug(offense)}", self._range(from_, to)
        )
        return SummarizedResponse.model_validate(data)

    def summarized_agency(
        self, ori: str, offense: Offense | str, from_: str | date, to: str | date
    ) -> SummarizedResponse:
        data = self._get_json(f"summarized/agency/{ori}/{_slug(offense)}", self._range(from_, to))
        return SummarizedResponse.model_validate(data)

    # -- arrests -----------------------------------------------------------
    def arrests_national(
        self,
        offense: Offense | str = "all",
        *,
        arrest_type: ArrestType | str = ArrestType.TOTALS,
        from_: str | date,
        to: str | date,
    ) -> ArrestTotalsResponse | ChartResponse:
        return self._arrests(f"arrest/national/{_slug(offense)}", arrest_type, from_, to)

    def arrests_state(
        self,
        state: str,
        offense: Offense | str = "all",
        *,
        arrest_type: ArrestType | str = ArrestType.TOTALS,
        from_: str | date,
        to: str | date,
    ) -> ArrestTotalsResponse | ChartResponse:
        return self._arrests(
            f"arrest/state/{state.upper()}/{_slug(offense)}", arrest_type, from_, to
        )

    def _arrests(
        self,
        path: str,
        arrest_type: ArrestType | str,
        from_: str | date,
        to: str | date,
    ) -> ArrestTotalsResponse | ChartResponse:
        atype = _arrest_type(arrest_type)
        params = {**self._range(from_, to), "type": atype}
        data = self._get_json(path, params)
        if atype == ArrestType.COUNTS.value:
            return ChartResponse.model_validate(data)
        return ArrestTotalsResponse.model_validate(data)

    # -- police employment (yearly) ---------------------------------------
    # Use the canonical spec paths (`/pe`, `/pe/{state}`). The `/pe/national`
    # and `/pe/state/{ST}` variants answer 200 but return all-null values.
    def police_employment_national(self, from_: str | date, to: str | date) -> ChartResponse:
        data = self._get_json("pe", self._range(from_, to, yearly=True))
        return ChartResponse.model_validate(data)

    def police_employment_state(
        self, state: str, from_: str | date, to: str | date
    ) -> ChartResponse:
        data = self._get_json(f"pe/{state.upper()}", self._range(from_, to, yearly=True))
        return ChartResponse.model_validate(data)
