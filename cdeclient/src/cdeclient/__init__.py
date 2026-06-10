"""Typed client for the FBI Crime Data Explorer (CDE) API."""

from __future__ import annotations

from .client import CdeClient, CdeError, CdeServerError
from .config import Settings
from .constants import (
    ARREST_OFFENSE_CODES,
    ARREST_OFFENSES,
    EXPANDED_PROPERTY_OFFENSES,
    LESDC_CHART_TYPES,
    NIBRS_OFFENSES,
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
    LesdcResponse,
    NibrsResponse,
    Offenses,
    PropertyResponse,
    ShrResponse,
    SummarizedResponse,
)

__all__ = [
    "ARREST_OFFENSES",
    "ARREST_OFFENSE_CODES",
    "EXPANDED_PROPERTY_OFFENSES",
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
    "LESDC_CHART_TYPES",
    "LesdcResponse",
    "NIBRS_OFFENSES",
    "NibrsResponse",
    "Offense",
    "PropertyResponse",
    "ShrResponse",
    "Offenses",
    "Settings",
    "SummarizedResponse",
]

__version__ = "0.1.0"
