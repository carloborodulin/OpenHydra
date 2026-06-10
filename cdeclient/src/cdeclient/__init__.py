"""Typed client for the FBI Crime Data Explorer (CDE) API."""

from __future__ import annotations

from .client import CdeClient, CdeError, CdeServerError
from .config import Settings
from .constants import (
    ARREST_OFFENSE_CODES,
    ARREST_OFFENSES,
    STATES,
    ArrestOffenseInfo,
    ArrestType,
    Offense,
    arrest_code,
)
from .models import (
    Agency,
    ArrestTotalsResponse,
    CdeProperties,
    ChartResponse,
    HateCrimeResponse,
    Offenses,
    ShrResponse,
    SummarizedResponse,
)

__all__ = [
    "ARREST_OFFENSES",
    "ARREST_OFFENSE_CODES",
    "STATES",
    "Agency",
    "ArrestOffenseInfo",
    "ArrestTotalsResponse",
    "ArrestType",
    "arrest_code",
    "CdeClient",
    "CdeError",
    "CdeProperties",
    "CdeServerError",
    "ChartResponse",
    "HateCrimeResponse",
    "Offense",
    "ShrResponse",
    "Offenses",
    "Settings",
    "SummarizedResponse",
]

__version__ = "0.1.0"
