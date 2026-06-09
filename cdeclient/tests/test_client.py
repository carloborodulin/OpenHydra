from __future__ import annotations

from collections.abc import Callable
from typing import Any

import respx
from httpx import Response

from cdeclient.client import CdeClient
from cdeclient.constants import ARREST_OFFENSE_CODES, Offense

BASE = "https://api.test/crime/fbi/cde"


def _client() -> CdeClient:
    # Zero-wait, no-op sleep so retry tests run instantly.
    return CdeClient(
        api_key="test-key",
        base_url=BASE,
        base_wait=0,
        max_wait=0,
        sleep=lambda _: None,
    )


@respx.mock
def test_agencies_builds_url_and_injects_key(sample: Callable[[str], Any]) -> None:
    route = respx.get(f"{BASE}/agency/byStateAbbr/NY").mock(
        return_value=Response(200, json=sample("agency_by_state_NY"))
    )
    with _client() as c:
        out = c.agencies_by_state("ny")  # lower-case → upper-cased in the path

    assert route.called
    assert route.calls.last.request.url.params["API_KEY"] == "test-key"
    counties = list(out)
    assert out[counties[0]][0].ori


@respx.mock
def test_retries_on_503_then_succeeds(sample: Callable[[str], Any]) -> None:
    route = respx.get(f"{BASE}/summarized/national/homicide").mock(
        side_effect=[
            Response(503),
            Response(200, json=sample("summarized_national_homicide")),
        ]
    )
    with _client() as c:
        r = c.summarized_national("homicide", "01-2020", "12-2022")

    assert route.call_count == 2
    assert "United States Offenses" in r.offenses.rates


@respx.mock
def test_summarized_normalizes_date_range_and_offense_enum() -> None:
    route = respx.get(f"{BASE}/summarized/national/violent-crime").mock(
        return_value=Response(200, json={"offenses": {"rates": {}, "actuals": {}}})
    )
    with _client() as c:
        c.summarized_national(Offense.VIOLENT_CRIME, "2020-01", "2022-12")

    params = route.calls.last.request.url.params
    assert params["from"] == "01-2020"  # YYYY-MM normalized to MM-YYYY
    assert params["to"] == "12-2022"


@respx.mock
def test_pe_uses_canonical_path_and_year_range() -> None:
    # The canonical `/pe` path returns real data; `/pe/national` returns all-null.
    route = respx.get(f"{BASE}/pe").mock(
        return_value=Response(200, json={"rates": {}, "actuals": {}})
    )
    with _client() as c:
        c.police_employment_national("2018", "2022")

    params = route.calls.last.request.url.params
    assert params["from"] == "2018"
    assert params["to"] == "2022"


@respx.mock
def test_pe_state_uses_canonical_path() -> None:
    route = respx.get(f"{BASE}/pe/NY").mock(
        return_value=Response(200, json={"rates": {}, "actuals": {}})
    )
    with _client() as c:
        c.police_employment_state("ny", "2018", "2022")

    assert route.called


def test_arrest_offense_codes_cover_all_offenses() -> None:
    # Every summarized offense slug has an arrest code; aggregates fall back to "all".
    assert set(ARREST_OFFENSE_CODES) == set(Offense)
    assert ARREST_OFFENSE_CODES[Offense.HOMICIDE] == "11"
    assert ARREST_OFFENSE_CODES[Offense.VIOLENT_CRIME] == "all"
