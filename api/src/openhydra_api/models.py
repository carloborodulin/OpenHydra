"""Pydantic response models for the API."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ArrestOffense(BaseModel):
    slug: str
    code: str
    name: str
    category: str
    # True for violent-crime and property-crime: the sum of 4 Part I offenses.
    derived: bool = False
    # True when the national snapshot has rows for this offense. The others are
    # available only through the live agency route.
    in_snapshot: bool = False


class SnapshotDomain(BaseModel):
    """One file of the release: when it was extracted and the window it covers."""

    domain: str
    extracted_at: datetime | None = None
    window_from: str | None = None
    window_to: str | None = None
    row_count: int | None = None
    status: str | None = None


class Snapshot(BaseModel):
    """The data release that the warehouse holds (from meta_snapshot)."""

    release_id: str
    promoted_at: datetime | None = None
    extracted_at_min: datetime | None = None
    extracted_at_max: datetime | None = None
    window_from: str | None = None
    window_to: str | None = None
    source: str | None = None
    # True when the dates come from git history, not from an extract manifest.
    reconstructed: bool = False
    domains: list[SnapshotDomain] = []


class Capabilities(BaseModel):
    # True when the server has an API key for the live agency routes. The key
    # itself is never sent.
    live_agency: bool = False


class Meta(BaseModel):
    snapshot: Snapshot | None = None
    capabilities: Capabilities = Capabilities()
    offenses: list[str]
    states: list[str]
    levels: list[str]
    arrest_offenses: list[ArrestOffense] = []
    arrest_categories: list[str] = []


class OffenseMonthly(BaseModel):
    period: date
    offenses_rate: float | None = None
    offenses_actual: float | None = None
    clearances_rate: float | None = None
    clearances_actual: float | None = None
    clearance_ratio: float | None = None
    # Trailing-12-month trend metrics (warehouse-derived; null for live agency rows).
    # ttm_rate is null unless all 12 calendar months have a rate (ttm_months = 12).
    ttm_months: int | None = None
    ttm_rate: float | None = None
    yoy_delta: float | None = None  # YoY change in the trailing-12-month rate
    # ttm_rate / mean monthly rate of calendar 2019 x 100 (December 2019 = 100).
    index_2019: float | None = None


class BenchmarkRow(BaseModel):
    period: date
    area_rate: float | None = None  # selected area's offense rate /100k
    national_rate: float | None = None  # national rate for the same offense/month
    relative_index: float | None = None  # area_rate / national_rate * 100 (100 = national)


class AgencyPoints(BaseModel):
    """Agencies in column form: item i of each list is one agency."""

    release_id: str | None = None
    ori: list[str]
    name: list[str | None]
    county: list[str | None]
    lat: list[float | None]
    lon: list[float | None]
    nibrs: list[bool | None]
    nibrs_start_year: list[int | None]


class AgencyFeature(BaseModel):
    ori: str
    agency_name: str | None = None
    agency_type: str | None = None
    county: str | None = None
    state_abbr: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_nibrs: bool | None = None
    nibrs_start_year: int | None = None


class ArrestRow(BaseModel):
    category: str
    label: str
    value: float | None = None


class PropertyRow(ArrestRow):
    """An expanded property row. A null year means a total over the whole window."""

    year: int | None = None


class PropertyYears(BaseModel):
    years: list[int]
    # True when the snapshot holds window totals with no year (an older extract).
    window_total: bool = False


class ArrestBreakdownRow(ArrestRow):
    """An arrest breakdown row with its offense, so a row can never lose it."""

    offense: str
    is_derived: bool = False


class ArrestAvailability(BaseModel):
    level: str
    area: str
    offenses: list[str]


class PoliceEmploymentRow(BaseModel):
    section: str
    metric: str
    year: int
    value: float | None = None


class PopulationRow(BaseModel):
    year: int
    population: int


class LesdcRow(BaseModel):
    section: str  # S (suicide) | AS (attempted suicide)
    label: str
    value: float | None = None


class UofParticipationRow(BaseModel):
    year: int
    participating_agencies: float | None = None
    total_agencies: float | None = None
    participation_percent: float | None = None
