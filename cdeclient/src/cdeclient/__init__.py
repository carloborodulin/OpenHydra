"""Typed client for the FBI Crime Data Explorer (CDE) API."""

from __future__ import annotations

from .client import CdeClient, CdeError, CdeServerError
from .config import Settings
from .constants import ARREST_OFFENSE_CODES, STATES, ArrestType, Offense
from .models import (
    Agency,
    ArrestTotalsResponse,
    CdeProperties,
    ChartResponse,
    Offenses,
    SummarizedResponse,
)

__all__ = [
    "ARREST_OFFENSE_CODES",
    "STATES",
    "Agency",
    "ArrestTotalsResponse",
    "ArrestType",
    "CdeClient",
    "CdeError",
    "CdeProperties",
    "CdeServerError",
    "ChartResponse",
    "Offense",
    "Offenses",
    "Settings",
    "SummarizedResponse",
]

__version__ = "0.1.0"
