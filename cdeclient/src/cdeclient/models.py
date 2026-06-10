"""Pydantic models for CDE API responses.

The CDE API mixes strict records (agencies) with loosely-keyed chart payloads
(series names and demographic labels vary per request), so the chart models keep
``extra="allow"`` and expose the stable parts (``rates``/``actuals`` time series
and ``cde_properties``) as typed fields.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# series name -> period (MM-YYYY or YYYY) -> value
TimeSeries = dict[str, dict[str, float | None]]


class CdeProperties(BaseModel):
    model_config = ConfigDict(extra="allow")

    # The API returns these either as a string or as a {source: date} dict
    # (e.g. {"UCR": "05/2026"}), so keep them untyped.
    max_data_date: Any = None
    last_refresh_date: Any = None


class Agency(BaseModel):
    """A reporting agency (ORI), as returned by /agency/byStateAbbr."""

    model_config = ConfigDict(extra="allow")

    ori: str
    agency_name: str
    agency_type_name: str | None = None
    counties: str | None = None
    state_abbr: str | None = None
    state_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_nibrs: bool | None = None
    nibrs_start_date: str | None = None


AgenciesByCounty = dict[str, list[Agency]]


class _Envelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    populations: dict[str, Any] = Field(default_factory=dict)
    tooltips: dict[str, Any] = Field(default_factory=dict)
    cde_properties: CdeProperties | None = None

    @field_validator("populations", "tooltips", mode="before")
    @classmethod
    def _null_to_empty(cls, value: Any) -> Any:
        # Some responses (e.g. /pe) send these as null rather than {}.
        return {} if value is None else value


class Offenses(BaseModel):
    model_config = ConfigDict(extra="allow")

    rates: TimeSeries = Field(default_factory=dict)
    actuals: TimeSeries = Field(default_factory=dict)

    @field_validator("rates", "actuals", mode="before")
    @classmethod
    def _series_null_to_empty(cls, value: Any) -> Any:
        # Sparse areas (e.g. an agency with no reported data) send rates/actuals
        # as null rather than {}; coerce so validation still passes.
        return {} if value is None else value


class SummarizedResponse(_Envelope):
    """/summarized/* — monthly offense & clearance series under ``offenses``."""

    offenses: Offenses


class ChartResponse(_Envelope):
    """Shared shape for /arrest?type=counts and /pe (top-level rates/actuals)."""

    rates: TimeSeries = Field(default_factory=dict)
    actuals: TimeSeries = Field(default_factory=dict)

    @field_validator("rates", "actuals", mode="before")
    @classmethod
    def _series_null_to_empty(cls, value: Any) -> Any:
        return {} if value is None else value


class ArrestTotalsResponse(_Envelope):
    """/arrest?type=totals — demographic breakdowns as extra fields.

    Each breakdown (e.g. ``"Arrestee Sex"``) maps a label to a count; access them
    uniformly via :attr:`breakdowns`.
    """

    @property
    def breakdowns(self) -> dict[str, Any]:
        extra = self.__pydantic_extra__ or {}
        return {key: value for key, value in extra.items() if isinstance(value, dict)}


class HateCrimeResponse(BaseModel):
    """/hate-crime/* (type=totals, and the state/agency variants).

    Two sections of dimensional breakdowns: ``bias_section`` (victim_type,
    offense_type, location_type, offender_race, offender_ethnicity,
    judicial_district) and ``incident_section`` (bias, bias_category). Each
    dimension maps a label to a count; access them merged — one entry per
    dimension — via :attr:`breakdowns`, the same shape as
    :attr:`ArrestTotalsResponse.breakdowns`.

    (The ``type=counts`` variant returns the top-level rates/actuals shape and is
    parsed with :class:`ChartResponse` instead.)
    """

    model_config = ConfigDict(extra="allow")

    bias_section: dict[str, Any] = Field(default_factory=dict)
    incident_section: dict[str, Any] = Field(default_factory=dict)

    @field_validator("bias_section", "incident_section", mode="before")
    @classmethod
    def _null_to_empty(cls, value: Any) -> Any:
        return {} if value is None else value

    @property
    def breakdowns(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for section in (self.bias_section, self.incident_section):
            for dimension, mapping in section.items():
                if isinstance(mapping, dict):
                    merged[dimension] = mapping
        return merged


class _VictimOffenderBreakdowns(BaseModel):
    """Shared totals shape for SHR + NIBRS: ``victim``, ``offense``, and
    ``offender`` sections, each a set of ``{label: count}`` dimensions. Exposed
    via :attr:`breakdowns` as ``{"<section>_<dimension>": {label: count}}`` (e.g.
    ``victim_age``, ``offender_race``, ``offense_weapons``) so victim/offender
    dimensions of the same name don't collide.

    (The ``type=counts`` variant returns the rates/actuals shape — parse it with
    :class:`ChartResponse` / :class:`SummarizedResponse`.)
    """

    model_config = ConfigDict(extra="allow")

    victim: dict[str, Any] = Field(default_factory=dict)
    offense: dict[str, Any] = Field(default_factory=dict)
    offender: dict[str, Any] = Field(default_factory=dict)

    @field_validator("victim", "offense", "offender", mode="before")
    @classmethod
    def _null_to_empty(cls, value: Any) -> Any:
        return {} if value is None else value

    @property
    def breakdowns(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for name, section in (
            ("victim", self.victim),
            ("offense", self.offense),
            ("offender", self.offender),
        ):
            if not isinstance(section, dict):
                continue
            for dimension, mapping in section.items():
                if isinstance(mapping, dict):
                    merged[f"{name}_{dimension}"] = mapping
        return merged


class ShrResponse(_VictimOffenderBreakdowns):
    """/shr/* type=totals — Supplementary Homicide Report breakdowns (victim &
    offender: age/sex/race/ethnicity; offense: weapons/circumstance/relationship)."""


class NibrsResponse(_VictimOffenderBreakdowns):
    """/nibrs/* type=totals — incident-based breakdowns. Same victim/offense/
    offender sections as SHR, with extra dimensions (victim location &
    relationship, offense related_offenses)."""


class LesdcResponse(BaseModel):
    """/lesdc?chartType=&year= — one chart's data for a year (national only).

    The API wraps it as a single-element list whose one (chart-specific) key maps
    to ``{"S": ..., "AS": ...}`` — Suicide and Attempted-Suicide sections. This
    model normalizes to :attr:`sections`. Section values are chart-shaped (a
    ``{label: count}`` map, or a list of ``{count, description}`` records, or a
    totals record), so flatten them in the warehouse normalizer.
    """

    sections: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: Any) -> LesdcResponse:
        sections: dict[str, Any] = {}
        if isinstance(payload, list) and payload and isinstance(payload[0], dict):
            for value in payload[0].values():
                if isinstance(value, dict):
                    sections = value
                    break
        return cls(sections=sections)


class PropertyResponse(BaseModel):
    """/supplemental/* type=totals — expanded property (stolen/recovered values
    and offense analysis).

    Sections ``offense_analysis`` (location/monetary counts & average values) and
    ``stolen_and_recovered`` (stolen_value, recovered_value). Each sub-dimension
    maps a label to a value; some are null for a given offense. Dimension names
    are unique across the two sections, so :attr:`breakdowns` keys on the
    dimension directly (e.g. ``stolen_value``, ``location_counts``).
    """

    model_config = ConfigDict(extra="allow")

    offense_analysis: dict[str, Any] = Field(default_factory=dict)
    stolen_and_recovered: dict[str, Any] = Field(default_factory=dict)

    @field_validator("offense_analysis", "stolen_and_recovered", mode="before")
    @classmethod
    def _null_to_empty(cls, value: Any) -> Any:
        return {} if value is None else value

    @property
    def breakdowns(self) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        for section in (self.offense_analysis, self.stolen_and_recovered):
            if not isinstance(section, dict):
                continue
            for dimension, mapping in section.items():
                if isinstance(mapping, dict):
                    merged[dimension] = mapping
        return merged
