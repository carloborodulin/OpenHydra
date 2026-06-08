"""Helpers for the API's two date formats: ``MM-YYYY`` and ``YYYY``."""

from __future__ import annotations

import re
from datetime import date

_MM_YYYY = re.compile(r"^(0[1-9]|1[0-2])-(\d{4})$")
_YYYY_MM = re.compile(r"^(\d{4})[-/](0[1-9]|1[0-2])$")
_YYYY = re.compile(r"^\d{4}$")


def to_month(value: str | date) -> str:
    """Normalize a value to the API's ``MM-YYYY`` month format.

    Accepts ``MM-YYYY``, ``YYYY-MM``/``YYYY/MM``, or a :class:`datetime.date`.
    """
    if isinstance(value, date):
        return f"{value.month:02d}-{value.year}"
    s = str(value).strip()
    if _MM_YYYY.match(s):
        return s
    m = _YYYY_MM.match(s)
    if m:
        return f"{m.group(2)}-{m.group(1)}"
    raise ValueError(f"Expected a month as MM-YYYY or YYYY-MM, got {value!r}")


def to_year(value: str | int | date) -> str:
    """Normalize a value to the API's 4-digit ``YYYY`` format (used by /pe)."""
    if isinstance(value, date):
        return str(value.year)
    s = str(value).strip()
    if _YYYY.match(s):
        return s
    raise ValueError(f"Expected a 4-digit year, got {value!r}")
