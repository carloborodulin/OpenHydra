"""Enumerated values accepted by the CDE API."""

from __future__ import annotations

from enum import StrEnum


class Offense(StrEnum):
    """Offense slugs accepted by the summarized endpoints (hyphenated)."""

    VIOLENT_CRIME = "violent-crime"
    HOMICIDE = "homicide"
    RAPE = "rape"
    ROBBERY = "robbery"
    AGGRAVATED_ASSAULT = "aggravated-assault"
    PROPERTY_CRIME = "property-crime"
    BURGLARY = "burglary"
    LARCENY = "larceny"
    MOTOR_VEHICLE_THEFT = "motor-vehicle-theft"
    ARSON = "arson"


class ArrestType(StrEnum):
    """``type`` query value for the /arrest endpoints."""

    TOTALS = "totals"  # aggregated demographic breakdowns
    COUNTS = "counts"  # monthly time series


# 50 states + DC (the API uses USPS two-letter abbreviations).
STATES: tuple[str, ...] = (
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DE",
    "DC",
    "FL",
    "GA",
    "HI",
    "ID",
    "IL",
    "IN",
    "IA",
    "KS",
    "KY",
    "LA",
    "ME",
    "MD",
    "MA",
    "MI",
    "MN",
    "MS",
    "MO",
    "MT",
    "NE",
    "NV",
    "NH",
    "NJ",
    "NM",
    "NY",
    "NC",
    "ND",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VT",
    "VA",
    "WA",
    "WV",
    "WI",
    "WY",
)
