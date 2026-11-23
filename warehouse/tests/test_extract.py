"""Extractor control flow with a counting fake client (no network)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import polars as pl
from cdeclient.models import ArrestTotalsResponse

from openhydra_etl.extract import Extractor


class CountingArrests:
    def __init__(self, resp: ArrestTotalsResponse) -> None:
        self.resp = resp
        self.calls: Counter[tuple[str, str]] = Counter()

    def arrests_national(self, code: str, *, from_: str, to: str) -> ArrestTotalsResponse:
        self.calls[("US", code)] += 1
        return self.resp

    def arrests_state(self, state: str, code: str, *, from_: str, to: str) -> ArrestTotalsResponse:
        self.calls[(state, code)] += 1
        return self.resp


def test_arrests_fetch_each_code_once_per_area(
    tmp_path: Path, sample: Callable[[str], Any]
) -> None:
    fake = CountingArrests(ArrestTotalsResponse.model_validate(sample("arrest_state_NY_all")))
    ex = Extractor(fake, tmp_path)  # type: ignore[arg-type]
    # "homicide" also appears inside violent-crime; "11" is homicide's raw code.
    frame = ex.pull_arrests(
        ["NY"], ["violent-crime", "homicide", "11", "all", "property-crime"], "01-2015", "12-2024"
    )
    codes = {"11", "20", "30", "50", "all", "60", "70", "90", "110"}
    for area in ("US", "NY"):
        assert {c for (a, c) in fake.calls if a == area} == codes
    assert all(n == 1 for n in fake.calls.values())

    # One canonical slug per code. The rollups are not written: dbt sums them.
    assert set(frame["offense"].unique()) == {
        "homicide",
        "rape",
        "robbery",
        "aggravated-assault",
        "all",
        "burglary",
        "larceny",
        "motor-vehicle-theft",
        "arson",
    }
    assert frame.filter(pl.col("offense") == "violent-crime").height == 0
    grain = ["level", "area", "offense", "category", "label"]
    assert frame.select(grain).is_duplicated().sum() == 0
    assert set(frame["window_from"].unique()) == {"01-2015"}
    assert set(frame["window_to"].unique()) == {"12-2024"}
    assert (tmp_path / "arrests.parquet").exists()
