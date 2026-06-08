from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import TypeAdapter

from cdeclient.models import (
    Agency,
    ArrestTotalsResponse,
    ChartResponse,
    SummarizedResponse,
)


def test_agencies_parse(sample: Callable[[str], Any]) -> None:
    parsed = TypeAdapter(dict[str, list[Agency]]).validate_python(sample("agency_by_state_NY"))
    counties = list(parsed)
    assert counties
    first = parsed[counties[0]][0]
    assert first.ori
    assert first.agency_name


def test_summarized_parse(sample: Callable[[str], Any]) -> None:
    r = SummarizedResponse.model_validate(sample("summarized_national_homicide"))
    assert "United States Offenses" in r.offenses.rates
    assert "United States Clearances" in r.offenses.rates
    assert r.cde_properties is not None


def test_arrest_totals_breakdowns(sample: Callable[[str], Any]) -> None:
    r = ArrestTotalsResponse.model_validate(sample("arrest_national_all_totals"))
    assert "Arrestee Sex" in r.breakdowns
    assert "Arrestee Race" in r.breakdowns


def test_arrest_counts_timeseries(sample: Callable[[str], Any]) -> None:
    r = ChartResponse.model_validate(sample("arrest_national_all_counts"))
    assert "United States Arrests" in r.rates


def test_pe_parse(sample: Callable[[str], Any]) -> None:
    r = ChartResponse.model_validate(sample("pe_national"))
    assert "Male Officers" in r.actuals
