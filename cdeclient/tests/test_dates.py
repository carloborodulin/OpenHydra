from __future__ import annotations

from datetime import date

import pytest

from cdeclient.dates import to_month, to_year


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
