from __future__ import annotations

from collections.abc import Callable
from typing import Any

import respx
from httpx import Response

from cdeclient.client import CdeClient
from cdeclient.constants import ARREST_OFFENSE_CODES, ARREST_OFFENSES, Offense, arrest_code

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
def test_agencies_guam_metadata_envelope_yields_empty(sample: Callable[[str], Any]) -> None:
    # Guam (GM) returns a metadata envelope ({"cde_agencies_query": {...}}) with no
    # county→agency lists; it must parse to an empty mapping, not raise.
    route = respx.get(f"{BASE}/agency/byStateAbbr/GM").mock(
        return_value=Response(200, json=sample("agency_by_state_GM"))
    )
    with _client() as c:
        out = c.agencies_by_state("GM")

    assert route.called
    assert out == {}


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


@respx.mock
def test_arrests_agency_builds_path(sample: Callable[[str], Any]) -> None:
    route = respx.get(f"{BASE}/arrest/agency/NY0303000/11").mock(
        return_value=Response(200, json=sample("arrest_state_NY_all"))
    )
    with _client() as c:
        c.arrests_agency("NY0303000", "11", from_="01-2020", to="12-2022")

    assert route.called
    params = route.calls.last.request.url.params
    assert params["type"] == "totals"
    assert params["from"] == "01-2020"


@respx.mock
def test_pe_agency_uses_state_and_ori_path() -> None:
    route = respx.get(f"{BASE}/pe/NY/NY0303000").mock(
        return_value=Response(200, json={"rates": {}, "actuals": {}})
    )
    with _client() as c:
        c.police_employment_agency("ny", "NY0303000", "2018", "2022")

    assert route.called
    params = route.calls.last.request.url.params
    assert params["from"] == "2018"  # yearly range, not MM-YYYY


@respx.mock
def test_summarized_tolerates_null_series_for_sparse_area() -> None:
    # An agency with no reported data returns offenses.actuals = null (not {}).
    respx.get(f"{BASE}/summarized/agency/ZZ9999999/homicide").mock(
        return_value=Response(200, json={"offenses": {"rates": None, "actuals": None}})
    )
    with _client() as c:
        r = c.summarized_agency("ZZ9999999", "homicide", "01-2020", "12-2022")
    assert r.offenses.rates == {} and r.offenses.actuals == {}


@respx.mock
def test_pe_tolerates_null_series() -> None:
    respx.get(f"{BASE}/pe/NY/NY0303000").mock(
        return_value=Response(200, json={"rates": None, "actuals": None})
    )
    with _client() as c:
        r = c.police_employment_agency("NY", "NY0303000", "2018", "2022")
    assert r.rates == {} and r.actuals == {}


def test_arrest_offense_codes_cover_all_offenses() -> None:
    # Every summarized offense slug has an arrest code; aggregates fall back to "all".
    assert set(ARREST_OFFENSE_CODES) == set(Offense)
    assert ARREST_OFFENSE_CODES[Offense.HOMICIDE] == "11"
    assert ARREST_OFFENSE_CODES[Offense.VIOLENT_CRIME] == "all"


def test_arrest_offenses_taxonomy_is_complete() -> None:
    # All 48 arrest_offense codes from the API enum are mapped, each unique.
    assert len(ARREST_OFFENSES) == 48
    assert len({info.code for info in ARREST_OFFENSES.values()}) == 48
    # The single-code Part I slugs align with the summarized Offense slugs.
    assert ARREST_OFFENSES["homicide"].code == "11"
    assert ARREST_OFFENSES["drug-abuse-violations"].category == "Drug/Narcotic Offenses"


def test_arrest_code_resolves_slugs_and_codes() -> None:
    assert arrest_code("homicide") == "11"  # arrest slug (also a summarized slug)
    assert arrest_code("drug-abuse-violations") == "150"  # arrest-only slug
    assert arrest_code("violent-crime") == "all"  # summarized aggregate -> all
    assert arrest_code("150") == "150"  # raw code passes through
    assert arrest_code("nonsense") == "all"  # unknown -> all
    assert arrest_code(None) == "all"
    assert arrest_code("") == "all"
