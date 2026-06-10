from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any

import polars as pl
from cdeclient.models import (
    Agency,
    ArrestTotalsResponse,
    ChartResponse,
    HateCrimeResponse,
    SummarizedResponse,
)
from pydantic import TypeAdapter

from openhydra_etl import normalize


def test_summarized_to_frame(sample: Callable[[str], Any]) -> None:
    resp = SummarizedResponse.model_validate(sample("summarized_national_homicide"))
    df = normalize.summarized_to_frame(resp, level="national", area="US", offense="homicide")
    assert df.columns == list(normalize.SUMMARIZED_SCHEMA)
    assert df.height > 0
    assert df.schema["period"] == pl.Date
    assert set(df["series"].unique()) >= {"offenses", "clearances"}


def test_summarized_state_drops_national_benchmark(sample: Callable[[str], Any]) -> None:
    # A state query also returns a "United States ..." benchmark series; it must
    # be dropped so it doesn't collide with the state's own series and inflate
    # the rate via the mart's max() pivot.
    resp = SummarizedResponse.model_validate(sample("summarized_state_NY_violent"))
    df = normalize.summarized_to_frame(resp, level="state", area="NY", offense="violent-crime")
    # Exactly one row per (series, measure, period) — no benchmark duplicates.
    dup = df.group_by(["series", "measure", "period"]).len().filter(pl.col("len") > 1)
    assert dup.height == 0
    assert set(df["measure"].unique()) == {"rate", "actual"}
    assert df["period"].min() >= date(2000, 1, 1)


def test_agencies_to_frame(sample: Callable[[str], Any]) -> None:
    by_county = TypeAdapter(dict[str, list[Agency]]).validate_python(sample("agency_by_state_NY"))
    df = normalize.agencies_to_frame(by_county)
    assert df.columns == list(normalize.AGENCIES_SCHEMA)
    assert df.height > 100  # NY has 537 agencies
    assert df["ori"].null_count() == 0
    assert df.schema["latitude"] == pl.Float64


def test_arrests_to_frame(sample: Callable[[str], Any]) -> None:
    resp = ArrestTotalsResponse.model_validate(sample("arrest_national_all_totals"))
    df = normalize.arrests_to_frame(resp, level="national", area="US", offense="violent-crime")
    assert df.columns == list(normalize.ARRESTS_SCHEMA)
    assert df.height > 0
    assert "Arrestee Sex" in set(df["category"].unique())
    assert set(df["offense"].unique()) == {"violent-crime"}


def test_hate_crime_to_frame(sample: Callable[[str], Any]) -> None:
    resp = HateCrimeResponse.model_validate(sample("hate_crime_national_totals"))
    df = normalize.hate_crime_to_frame(resp, level="national", area="US")
    assert df.columns == list(normalize.HATE_CRIME_SCHEMA)
    assert df.height > 0
    cats = set(df["category"].unique())
    assert "bias_category" in cats  # from incident_section
    assert "offender_race" in cats  # from bias_section
    assert df["value"].null_count() == 0


def test_pe_to_frame(sample: Callable[[str], Any]) -> None:
    resp = ChartResponse.model_validate(sample("pe_national"))
    df = normalize.pe_to_frame(resp, level="national", area="US")
    assert df.columns == list(normalize.PE_SCHEMA)
    assert df.height > 0
    assert set(df["section"].unique()) <= {"rate", "actual"}
    assert df.schema["year"] == pl.Int32
