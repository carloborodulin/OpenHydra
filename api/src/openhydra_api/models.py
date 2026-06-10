"""Pydantic response models for the API."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class ArrestOffense(BaseModel):
    slug: str
    code: str
    name: str
    category: str


class Meta(BaseModel):
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


class PoliceEmploymentRow(BaseModel):
    section: str
    metric: str
    year: int
    value: float | None = None


class LesdcRow(BaseModel):
    section: str  # S (suicide) | AS (attempted suicide)
    label: str
    value: float | None = None


class UofParticipationRow(BaseModel):
    year: int
    participating_agencies: float | None = None
    total_agencies: float | None = None
    participation_percent: float | None = None
