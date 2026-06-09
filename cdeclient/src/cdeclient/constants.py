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


# The /arrest endpoints take a *numeric* offense code in the path, a different
# taxonomy from the hyphenated summarized slugs. This maps each summarized
# offense to its arrest code so the warehouse can key arrests on the same slug
# the rest of the app uses. Codes were verified against the live API by matching
# each code's total arrests to the labelled "Offense Name" breakdown of code
# "all". The two aggregate slugs (violent-crime, property-crime) have no single
# arrest code, so they fall back to "all" (all-offense demographics).
#   note: "rape" maps to the legacy rape code (20) — the only one carrying data;
#   the revised-definition rape codes return ~0 arrests.
ARREST_OFFENSE_CODES: dict[str, str] = {
    Offense.HOMICIDE: "11",
    Offense.RAPE: "20",
    Offense.ROBBERY: "30",
    Offense.AGGRAVATED_ASSAULT: "50",
    Offense.BURGLARY: "60",
    Offense.LARCENY: "70",
    Offense.MOTOR_VEHICLE_THEFT: "90",
    Offense.ARSON: "110",
    Offense.VIOLENT_CRIME: "all",
    Offense.PROPERTY_CRIME: "all",
}


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
