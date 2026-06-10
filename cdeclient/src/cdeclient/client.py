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
    HateCrimeResponse,
    LesdcResponse,
    NibrsEstimationResponse,
    NibrsResponse,
    PropertyResponse,
    ShrResponse,
    SummarizedResponse,
    UofParticipation,
    UofQuestionItem,
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
        """Agencies in a state, grouped by county.

        Most areas return ``{county: [agency, ...]}``. A few (notably Guam, GM)
        instead return a metadata envelope (``{"cde_agencies_query": {...}}``)
        with no agency list — keep only the county→list entries so those areas
        yield an empty mapping rather than raising a ``ValidationError``.
        """
        data = self._get_json(f"agency/byStateAbbr/{state.upper()}")
        if not isinstance(data, dict):
            return {}
        counties = {key: value for key, value in data.items() if isinstance(value, list)}
        return _AGENCIES_ADAPTER.validate_python(counties)

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

    def arrests_agency(
        self,
        ori: str,
        offense: Offense | str = "all",
        *,
        arrest_type: ArrestType | str = ArrestType.TOTALS,
        from_: str | date,
        to: str | date,
    ) -> ArrestTotalsResponse | ChartResponse:
        return self._arrests(f"arrest/agency/{ori}/{_slug(offense)}", arrest_type, from_, to)

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

    # -- hate crime --------------------------------------------------------
    # type=totals returns the dimensional-breakdown shape (bias_section +
    # incident_section). The state endpoint takes type; the agency endpoint
    # doesn't (it returns the same totals shape regardless).
    def hate_crime_national(self, from_: str | date, to: str | date) -> HateCrimeResponse:
        data = self._get_json("hate-crime/national", {**self._range(from_, to), "type": "totals"})
        return HateCrimeResponse.model_validate(data)

    def hate_crime_state(self, state: str, from_: str | date, to: str | date) -> HateCrimeResponse:
        data = self._get_json(
            f"hate-crime/state/{state.upper()}", {**self._range(from_, to), "type": "totals"}
        )
        return HateCrimeResponse.model_validate(data)

    def hate_crime_agency(self, ori: str, from_: str | date, to: str | date) -> HateCrimeResponse:
        data = self._get_json(f"hate-crime/agency/{ori}", self._range(from_, to))
        return HateCrimeResponse.model_validate(data)

    # -- expanded homicide / SHR -------------------------------------------
    # All three levels take type=totals (the breakdown shape). type=counts would
    # return the ChartResponse time series.
    def shr_national(self, from_: str | date, to: str | date) -> ShrResponse:
        data = self._get_json("shr/national", {**self._range(from_, to), "type": "totals"})
        return ShrResponse.model_validate(data)

    def shr_state(self, state: str, from_: str | date, to: str | date) -> ShrResponse:
        data = self._get_json(
            f"shr/state/{state.upper()}", {**self._range(from_, to), "type": "totals"}
        )
        return ShrResponse.model_validate(data)

    def shr_agency(self, ori: str, from_: str | date, to: str | date) -> ShrResponse:
        data = self._get_json(f"shr/agency/{ori}", {**self._range(from_, to), "type": "totals"})
        return ShrResponse.model_validate(data)

    # -- expanded property / supplemental ----------------------------------
    # offense is one of EXPANDED_PROPERTY_OFFENSES (NB, NL, NMVT, NROB).
    def property_national(
        self, offense: str, from_: str | date, to: str | date
    ) -> PropertyResponse:
        data = self._get_json(
            f"supplemental/national/{offense}", {**self._range(from_, to), "type": "totals"}
        )
        return PropertyResponse.model_validate(data)

    def property_state(
        self, state: str, offense: str, from_: str | date, to: str | date
    ) -> PropertyResponse:
        data = self._get_json(
            f"supplemental/state/{state.upper()}/{offense}",
            {**self._range(from_, to), "type": "totals"},
        )
        return PropertyResponse.model_validate(data)

    def property_agency(
        self, ori: str, offense: str, from_: str | date, to: str | date
    ) -> PropertyResponse:
        data = self._get_json(
            f"supplemental/agency/{ori}/{offense}", {**self._range(from_, to), "type": "totals"}
        )
        return PropertyResponse.model_validate(data)

    # -- NIBRS incidents ---------------------------------------------------
    # offense is a NIBRS code (NIBRS_OFFENSES lists the curated subset; any of the
    # 72 `nibrs_offenses` codes is accepted).
    def nibrs_national(self, offense: str, from_: str | date, to: str | date) -> NibrsResponse:
        data = self._get_json(
            f"nibrs/national/{offense}", {**self._range(from_, to), "type": "totals"}
        )
        return NibrsResponse.model_validate(data)

    def nibrs_state(
        self, state: str, offense: str, from_: str | date, to: str | date
    ) -> NibrsResponse:
        data = self._get_json(
            f"nibrs/state/{state.upper()}/{offense}", {**self._range(from_, to), "type": "totals"}
        )
        return NibrsResponse.model_validate(data)

    def nibrs_agency(
        self, ori: str, offense: str, from_: str | date, to: str | date
    ) -> NibrsResponse:
        data = self._get_json(
            f"nibrs/agency/{ori}/{offense}", {**self._range(from_, to), "type": "totals"}
        )
        return NibrsResponse.model_validate(data)

    # -- Use of Force (national; participation + report questions) ----------
    def uof_participation_national(
        self, year: str | int, quarter: str | int = 4
    ) -> UofParticipation:
        data = self._get_json(
            "participation/national/uof/nationalByYear",
            {"year": str(year), "quarter": str(quarter)},
        )
        return UofParticipation.from_payload(data)

    def uof_questions(
        self, year: str | int, grp: str = "A", quarter: str | int = 4
    ) -> list[UofQuestionItem]:
        data = self._get_json(f"uof/questions/{grp}/{year}/{quarter}", {})
        if not isinstance(data, list):
            return []
        return [UofQuestionItem.model_validate(x) for x in data if isinstance(x, dict)]

    # -- NIBRS estimations (modeled counts w/ confidence intervals) --------
    # offense is a numeric nibrs_estimations code; see /nibrs-estimation/lookup/all.
    def nibrs_estimation_lookup(self) -> Any:
        """Raw lookup payload: code maps for states, offenses, regions, etc."""
        return self._get_json("nibrs-estimation/lookup/all")

    def nibrs_estimation_national(self, offense: str, year: str | int) -> NibrsEstimationResponse:
        data = self._get_json(f"nibrs-estimation/national/{offense}", {"year": str(year)})
        return NibrsEstimationResponse.from_payload(data)

    def nibrs_estimation_region(
        self, region: str, offense: str, year: str | int
    ) -> NibrsEstimationResponse:
        data = self._get_json(f"nibrs-estimation/region/{region}/{offense}", {"year": str(year)})
        return NibrsEstimationResponse.from_payload(data)

    # -- LESDC (LE suicide data collection; national only, by chart type) ---
    def lesdc(self, chart_type: str, year: str | int) -> LesdcResponse:
        data = self._get_json("lesdc", {"chartType": chart_type, "year": str(year)})
        return LesdcResponse.from_payload(data)

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

    def police_employment_agency(
        self, state: str, ori: str, from_: str | date, to: str | date
    ) -> ChartResponse:
        """Agency-level LE employment via the canonical /pe/{state}/{ori} path.

        Agency / older cells are often null (sparse) — callers should tolerate
        empty series.
        """
        data = self._get_json(f"pe/{state.upper()}/{ori}", self._range(from_, to, yearly=True))
        return ChartResponse.model_validate(data)
