from __future__ import annotations

from datetime import date

import pytest

from cdeclient.dates import parse_window, to_month, to_year, year_of


def test_to_month_passthrough() -> None:
    assert to_month("01-2020") == "01-2020"


def test_to_month_from_iso_ordering() -> None:
    assert to_month("2020-01") == "01-2020"
    assert to_month("2020/01") == "01-2020"


def test_to_month_from_date() -> None:
    assert to_month(date(2020, 1, 15)) == "01-2020"


@pytest.mark.parametrize("bad", ["2020", "13-2020", "Jan-2020", ""])
def test_to_month_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        to_month(bad)


def test_to_year() -> None:
    assert to_year(2020) == "2020"
    assert to_year("2020") == "2020"
    assert to_year(date(2020, 6, 1)) == "2020"


@pytest.mark.parametrize("bad", ["20", "01-2020", "twenty"])
def test_to_year_rejects_garbage(bad: str) -> None:
    with pytest.raises(ValueError):
        to_year(bad)


@pytest.mark.parametrize(
    ("value", "year"),
    [("12-2024", "2024"), ("2024-12", "2024"), ("2024/02", "2024"), (date(2024, 2, 29), "2024")],
)
def test_year_of_handles_each_form(value: str | date, year: str) -> None:
    assert year_of(value) == year


def test_parse_window_normalizes_and_orders() -> None:
    assert parse_window("2015-01", "12-2024") == ("01-2015", "12-2024")
    assert parse_window(date(2020, 2, 29), "02-2020") == ("02-2020", "02-2020")
    with pytest.raises(ValueError, match="starts after"):
        parse_window("12-2024", "01-2015")
    with pytest.raises(ValueError):
        parse_window("13-2024", "12-2024")
