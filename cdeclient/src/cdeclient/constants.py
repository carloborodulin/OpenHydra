"""Enumerated values accepted by the CDE API."""

from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple


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


class ArrestOffenseInfo(NamedTuple):
    """Metadata for an arrest offense: its API path ``code``, display ``name``,
    and UCR group ``category``."""

    code: str
    name: str
    category: str


# The full arrest-offense taxonomy: all 48 codes the /arrest endpoints accept
# (the API's `arrest_offense` enum), keyed by a stable hyphenated slug. Codes,
# names, and categories were verified against the live API (see
# api_mapping_report.md §4). The eight single-code Part I offenses reuse the
# summarized `Offense` slugs (homicide, rape, robbery, …) so the two domains
# align; the remaining 39 codes plus the "all" rollup are arrest-specific.
ARREST_OFFENSES: dict[str, ArrestOffenseInfo] = {
    "all": ArrestOffenseInfo("all", "All Offenses", "All Offenses Rollup"),
    "homicide": ArrestOffenseInfo("11", "Murder and Nonnegligent Homicide", "Homicide Offenses"),
    "manslaughter-by-negligence": ArrestOffenseInfo(
        "12", "Manslaughter by Negligence", "Homicide Offenses"
    ),
    "rape": ArrestOffenseInfo("20", "Rape (Legacy)", "Sex Offenses"),
    "rape-revised": ArrestOffenseInfo("23", "Rape (Revised Definition)", "Sex Offenses"),
    "robbery": ArrestOffenseInfo("30", "Robbery", "Robbery"),
    "aggravated-assault": ArrestOffenseInfo("50", "Aggravated Assault", "Aggravated Assault"),
    "simple-assault": ArrestOffenseInfo("55", "Simple Assault", "Simple Assault"),
    "burglary": ArrestOffenseInfo("60", "Burglary", "Burglary"),
    "larceny": ArrestOffenseInfo("70", "Larceny", "Larceny"),
    "motor-vehicle-theft": ArrestOffenseInfo("90", "Motor Vehicle Theft", "Motor Vehicle Theft"),
    "human-trafficking-servitude": ArrestOffenseInfo(
        "101", "Human Trafficking (Involuntary Servitude)", "Human Trafficking"
    ),
    "human-trafficking-commercial-sex": ArrestOffenseInfo(
        "102", "Human Trafficking (Commercial Sex Acts)", "Human Trafficking"
    ),
    "arson": ArrestOffenseInfo("110", "Arson", "Arson"),
    "prostitution": ArrestOffenseInfo(
        "140", "Prostitution and Commercialized Vice", "Prostitution Offenses"
    ),
    "prostitution-assisting": ArrestOffenseInfo(
        "141", "Assisting or Promoting Prostitution", "Prostitution Offenses"
    ),
    "prostitution-purchasing": ArrestOffenseInfo(
        "142", "Purchasing Prostitution", "Prostitution Offenses"
    ),
    "prostitution-other": ArrestOffenseInfo(
        "143", "Other Prostitution / Commercial Sex", "Prostitution Offenses"
    ),
    "drug-abuse-violations": ArrestOffenseInfo(
        "150", "Drug Abuse Violations", "Drug/Narcotic Offenses"
    ),
    "drug-sale-opium-cocaine": ArrestOffenseInfo(
        "151", "Drug Sale/Manufacturing - Opium/Cocaine & derivatives", "Drug/Narcotic Offenses"
    ),
    "drug-sale-marijuana": ArrestOffenseInfo(
        "152", "Drug Sale/Manufacturing - Marijuana", "Drug/Narcotic Offenses"
    ),
    "drug-sale-synthetic": ArrestOffenseInfo(
        "153", "Drug Sale/Manufacturing - Synthetic Narcotics", "Drug/Narcotic Offenses"
    ),
    "drug-sale-other-dangerous": ArrestOffenseInfo(
        "154", "Drug Sale/Manufacturing - Other Dangerous Drugs", "Drug/Narcotic Offenses"
    ),
    "drug-sale-unspecified": ArrestOffenseInfo(
        "155", "Drug Sale/Manufacturing - Unspecified / Other", "Drug/Narcotic Offenses"
    ),
    "drug-possession-opium-cocaine": ArrestOffenseInfo(
        "156", "Drug Possession - Opium/Cocaine & derivatives", "Drug/Narcotic Offenses"
    ),
    "drug-possession-marijuana": ArrestOffenseInfo(
        "157", "Drug Possession - Marijuana", "Drug/Narcotic Offenses"
    ),
    "drug-possession-synthetic": ArrestOffenseInfo(
        "158", "Drug Possession - Synthetic Narcotics", "Drug/Narcotic Offenses"
    ),
    "drug-possession-other-dangerous": ArrestOffenseInfo(
        "159", "Drug Possession - Other Dangerous Drugs", "Drug/Narcotic Offenses"
    ),
    "drug-possession-unspecified": ArrestOffenseInfo(
        "160", "Drug Possession - Unspecified / Other", "Drug/Narcotic Offenses"
    ),
    "gambling": ArrestOffenseInfo("170", "Gambling", "Gambling Offenses"),
    "gambling-bookmaking": ArrestOffenseInfo("171", "Gambling - Bookmaking", "Gambling Offenses"),
    "gambling-numbers-lottery": ArrestOffenseInfo(
        "172", "Gambling - Numbers and Lottery", "Gambling Offenses"
    ),
    "gambling-other": ArrestOffenseInfo(
        "173", "Gambling - Other / Unspecified", "Gambling Offenses"
    ),
    "counterfeiting-forgery": ArrestOffenseInfo(
        "180", "Counterfeiting/Forgery", "Counterfeiting/Forgery"
    ),
    "fraud": ArrestOffenseInfo("190", "Fraud", "Fraud Offenses"),
    "embezzlement": ArrestOffenseInfo("200", "Embezzlement", "Embezzlement"),
    "stolen-property": ArrestOffenseInfo(
        "210", "Stolen Property (Buying, Receiving, Possessing)", "Stolen Property Offenses"
    ),
    "vandalism": ArrestOffenseInfo("220", "Vandalism", "Destruction/Damage/Vandalism of Property"),
    "weapons": ArrestOffenseInfo(
        "230", "Weapons (Carrying, Possessing, etc.)", "Weapon Law Violations"
    ),
    "sex-offenses": ArrestOffenseInfo(
        "240", "Sex Offenses (except Rape and Prostitution)", "Sex Offenses, Non-forcible"
    ),
    "family-offenses": ArrestOffenseInfo(
        "250", "Offenses Against the Family and Children", "Family Offenses, Nonviolent"
    ),
    "dui": ArrestOffenseInfo("260", "Driving Under the Influence", "Driving Under the Influence"),
    "liquor-laws": ArrestOffenseInfo("270", "Liquor Law Violations", "Liquor Law Violations"),
    "drunkenness": ArrestOffenseInfo("280", "Drunkenness", "Drunkenness"),
    "disorderly-conduct": ArrestOffenseInfo("290", "Disorderly Conduct", "Disorderly Conduct"),
    "vagrancy": ArrestOffenseInfo("300", "Vagrancy", "Vagrancy/Loitering"),
    "all-other-offenses": ArrestOffenseInfo("310", "All Other Offenses", "All Other Offenses"),
    "curfew-loitering": ArrestOffenseInfo(
        "330", "Curfew and Loitering Law Violations", "Vagrancy/Loitering"
    ),
}

# Reverse lookup: numeric code -> slug (e.g. "150" -> "drug-abuse-violations").
ARREST_CODE_TO_SLUG: dict[str, str] = {info.code: slug for slug, info in ARREST_OFFENSES.items()}


def arrest_code(offense: str | None) -> str:
    """Resolve an offense identifier to its numeric arrest code.

    Accepts an arrest slug (``ARREST_OFFENSES``), a summarized ``Offense`` slug
    (via ``ARREST_OFFENSE_CODES`` — the two aggregates resolve to ``"all"``), or a
    raw code already. Unknown / empty values fall back to ``"all"``.
    """
    if not offense:
        return "all"
    info = ARREST_OFFENSES.get(offense)
    if info is not None:
        return info.code
    summarized = ARREST_OFFENSE_CODES.get(offense)
    if summarized is not None:
        return summarized
    if offense in ARREST_CODE_TO_SLUG:  # already a raw code
        return offense
    return "all"


# /supplemental (expanded property) offense codes -> display name. These are the
# four property crimes the supplemental endpoints accept (the API's
# `expanded_property_offenses` enum).
EXPANDED_PROPERTY_OFFENSES: dict[str, str] = {
    "NB": "Burglary",
    "NL": "Larceny",
    "NMVT": "Motor Vehicle Theft",
    "NROB": "Robbery",
}


# A curated subset of the 72 NIBRS offense codes (the API's `nibrs_offenses`
# enum) used for the warehouse + UI selector — the common Group A crimes. The
# client/endpoints accept any of the 72 codes (so live agency drill-down can
# reach the long tail); only these are pre-materialized nationally/by-state.
NIBRS_OFFENSES: dict[str, str] = {
    "09A": "Murder & Nonnegligent Manslaughter",
    "11A": "Rape",
    "120": "Robbery",
    "13A": "Aggravated Assault",
    "13B": "Simple Assault",
    "200": "Arson",
    "220": "Burglary / Breaking & Entering",
    "23F": "Theft From Motor Vehicle",
    "240": "Motor Vehicle Theft",
    "250": "Counterfeiting / Forgery",
    "35A": "Drug / Narcotic Violations",
    "520": "Weapon Law Violations",
}


# 50 states + DC, plus three additional CDE reporting areas the API's `states`
# enum also accepts: FS (federal agencies), GM (Guam), VI (U.S. Virgin Islands).
# 54 total. The API uses USPS-style two-letter abbreviations.
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
    # Federal & territorial reporting areas (beyond the 50 states + DC):
    "FS",  # Federal agencies (DEA, FBI, etc.)
    "GM",  # Guam — returns a metadata envelope, no agency list (see agencies_by_state)
    "VI",  # U.S. Virgin Islands
)
