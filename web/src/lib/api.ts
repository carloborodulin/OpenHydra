export interface ArrestOffense {
  slug: string;
  code: string;
  name: string;
  category: string;
  // violent-crime and property-crime: the sum of their 4 Part I offenses.
  derived: boolean;
  // True when the national snapshot has rows. The others are live-only.
  in_snapshot: boolean;
}

export interface SnapshotDomain {
  domain: string;
  extracted_at: string | null;
  window_from: string | null;
  window_to: string | null;
  row_count: number | null;
  status: string | null;
}

/** The data release in the warehouse. Every warehouse view shows these facts. */
export interface Snapshot {
  release_id: string;
  promoted_at: string | null;
  extracted_at_min: string | null;
  extracted_at_max: string | null;
  window_from: string | null;
  window_to: string | null;
  source: string | null;
  // True when the dates come from git history, not from an extract manifest.
  reconstructed: boolean;
  domains: SnapshotDomain[];
}

export interface Meta {
  snapshot: Snapshot | null;
  capabilities: { live_agency: boolean };
  offenses: string[];
  states: string[];
  levels: string[];
  // The 48-code arrest taxonomy plus the 2 derived rollups, and the demographic
  // categories present in the warehouse (e.g. "Arrestee Race", "Arrestee Sex").
  arrest_offenses: ArrestOffense[];
  arrest_categories: string[];
}

export interface OffenseMonthly {
  period: string;
  offenses_rate: number | null;
  offenses_actual: number | null;
  clearances_rate: number | null;
  clearances_actual: number | null;
  clearance_ratio: number | null;
  // Trailing-12-month trend metrics (warehouse-derived; null for live agency rows).
  // ttm_rate is null unless all 12 calendar months have a rate (ttm_months = 12).
  ttm_months?: number | null;
  ttm_rate: number | null;
  yoy_delta: number | null; // YoY change in the trailing-12-month rate (fraction)
  index_2019: number | null; // ttm_rate ÷ the calendar-2019 mean rate × 100 (Dec 2019 = 100)
}

export interface ArrestRow {
  category: string;
  label: string;
  value: number | null;
}

/** An arrest row always says which offense it counts. */
export interface ArrestBreakdownRow extends ArrestRow {
  offense: string;
  is_derived: boolean;
}

export interface ArrestAvailability {
  level: string;
  area: string;
  offenses: string[];
}

export interface BenchmarkRow {
  period: string;
  area_rate: number | null;
  national_rate: number | null;
  relative_index: number | null; // area_rate / national_rate * 100 (100 = national)
}

export interface AgencyFeature {
  ori: string;
  agency_name: string | null;
  agency_type: string | null;
  county: string | null;
  state_abbr: string | null;
  latitude: number | null;
  longitude: number | null;
  is_nibrs: boolean | null;
  nibrs_start_year: number | null;
}

/** /api/agencies/points: agencies in column form (item i of each list is one agency). */
export interface AgencyPoints {
  release_id: string | null;
  ori: string[];
  name: (string | null)[];
  county: (string | null)[];
  lat: (number | null)[];
  lon: (number | null)[];
  nibrs: (boolean | null)[];
  nibrs_start_year: (number | null)[];
}

/** Rows from the column form, in the shape the views use. */
export function pointsToAgencies(p: AgencyPoints): AgencyFeature[] {
  return p.ori.map((ori, i) => ({
    ori,
    agency_name: p.name[i],
    agency_type: null,
    county: p.county[i],
    state_abbr: ori.slice(0, 2),
    latitude: p.lat[i],
    longitude: p.lon[i],
    is_nibrs: p.nibrs[i],
    nibrs_start_year: p.nibrs_start_year[i],
  }));
}

export interface PoliceEmploymentRow {
  section: string; // "rate" | "actual"
  metric: string;
  year: number;
  value: number | null;
}

/** A NIBRS estimate with the FBI interval (null in releases before 2026-11). */
export interface EstimateRow extends ArrestRow {
  lower: number | null;
  upper: number | null;
}

/** An expanded property row. A null year means a total over the whole window. */
export interface PropertyRow extends ArrestRow {
  year: number | null;
}

export interface PropertyYears {
  years: number[];
  // True when the snapshot holds window totals with no year (an older extract).
  window_total: boolean;
}

export interface PopulationRow {
  year: number;
  population: number;
}

export interface LesdcRow {
  section: string; // "S" (suicide) | "AS" (attempted suicide)
  label: string;
  value: number | null;
}

export interface UofParticipationRow {
  year: number;
  participating_agencies: number | null;
  total_agencies: number | null;
  participation_percent: number | null;
}

/**
 * An API failure with what the dashboard needs to explain it: the HTTP status,
 * the stable `code` of the API error body (see api/README.md) and Retry-After.
 * A network failure (offline, DNS) has status 0.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly retryAfter: number | null;

  constructor(status: number, code: string | null, retryAfter: number | null, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.retryAfter = retryAfter;
  }
}

// React Query passes an AbortSignal to each query function, so a stale request
// (for example after a quick region change) is cancelled. `withSignal` hands
// that signal to the fetch below: `get` reads it synchronously, before its first
// await, so no other call can see it.
let currentSignal: AbortSignal | undefined;

export function withSignal<T>(signal: AbortSignal | undefined, call: () => Promise<T>): Promise<T> {
  currentSignal = signal;
  try {
    return call();
  } finally {
    currentSignal = undefined;
  }
}

async function get<T>(path: string): Promise<T> {
  const signal = currentSignal;
  let res: Response;
  try {
    res = await fetch(path, { signal });
  } catch (err) {
    if (signal?.aborted) throw err;
    throw new ApiError(0, "network", null, "The network request failed.");
  }
  if (!res.ok) {
    let code: string | null = null;
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { code?: string; detail?: unknown };
      code = body.code ?? null;
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // Not a JSON error body.
    }
    const after = Number(res.headers.get("Retry-After"));
    throw new ApiError(
      res.status,
      code,
      Number.isFinite(after) && after > 0 ? after : null,
      detail,
    );
  }
  return res.json() as Promise<T>;
}

const qs = (params: Record<string, string | undefined>) =>
  Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(v as string)}`)
    .join("&");

export const api = {
  meta: () => get<Meta>("/api/v1/meta"),
  offensesMonthly: (offense: string, level = "national", area = "US") =>
    get<OffenseMonthly[]>(`/api/v1/offenses/monthly?${qs({ offense, level, area })}`),
  // Area offense rate alongside the national rate + a relative index (100 = national).
  offensesBenchmark: (offense: string, level = "state", area = "US") =>
    get<BenchmarkRow[]>(`/api/v1/offenses/benchmark?${qs({ offense, level, area })}`),
  arrests: (category: string, offense = "all", level = "national", area = "US") =>
    get<ArrestBreakdownRow[]>(`/api/v1/arrests?${qs({ level, area, offense, category })}`),
  arrestsAvailable: (level = "national", area = "US") =>
    get<ArrestAvailability>(`/api/v1/arrests/available?${qs({ level, area })}`),
  agencies: (state?: string) => get<AgencyFeature[]>(`/api/v1/agencies?${qs({ state })}`),
  // `v` is the release ID: with the current release the answer is immutable.
  agencyPoints: (release: string, state?: string) =>
    get<AgencyPoints>(`/api/v1/agencies/points?${qs({ state, v: release })}`),
  policeEmployment: (level = "national", area = "US") =>
    get<PoliceEmploymentRow[]>(`/api/v1/police-employment?${qs({ level, area })}`),
  population: (level = "national", area = "US") =>
    get<PopulationRow[]>(`/api/v1/population?${qs({ level, area })}`),
  // Hate crime breakdowns share the ArrestRow {category, label, value} shape;
  // `category` is the dimension (bias_category, offender_race, location_type, …).
  hateCrime: (category?: string, level = "national", area = "US") =>
    get<ArrestRow[]>(`/api/v1/hate-crime?${qs({ level, area, category })}`),
  // Expanded homicide (SHR); `category` is section_dimension (victim_age,
  // offense_weapons, offender_race, …).
  shr: (category?: string, level = "national", area = "US") =>
    get<ArrestRow[]>(`/api/v1/shr?${qs({ level, area, category })}`),
  // Expanded property; `offense` is NB/NL/NMVT/NROB.
  property: (offense: string, category?: string, level = "national", area = "US", year?: number) =>
    get<PropertyRow[]>(
      `/api/v1/property?${qs({ level, area, offense, category, year: year == null ? undefined : String(year) })}`,
    ),
  propertyYears: (offense: string, level = "national", area = "US") =>
    get<PropertyYears>(`/api/v1/property/years?${qs({ level, area, offense })}`),
  // NIBRS incidents; `offense` is a NIBRS code (e.g. 13A).
  nibrs: (offense: string, category?: string, level = "national", area = "US") =>
    get<ArrestRow[]>(`/api/v1/nibrs?${qs({ level, area, offense, category })}`),
  // LESDC (LE suicide data collection); national only, by year + chart type.
  lesdc: (chartType: string, year: number, section?: string) =>
    get<LesdcRow[]>(`/api/v1/lesdc?${qs({ chart_type: chartType, year: String(year), section })}`),
  // Use of Force; national only.
  uofParticipation: () => get<UofParticipationRow[]>("/api/v1/uof/participation"),
  uofQuestions: (year: number, category?: string) =>
    get<ArrestRow[]>(`/api/v1/uof/questions?${qs({ year: String(year), category })}`),
  // NIBRS estimations; national / region, numeric offense code.
  nibrsEstimation: (level: string, area: string, offense: string, category?: string) =>
    get<EstimateRow[]>(`/api/v1/nibrs-estimation?${qs({ level, area, offense, category })}`),

  // Agency drill-down: served live from the CDE API by the backend, same shapes.
  agencyOffenses: (ori: string, offense: string) =>
    get<OffenseMonthly[]>(`/api/v1/agency/${encodeURIComponent(ori)}/offenses?${qs({ offense })}`),
  agencyArrests: (ori: string, category: string, offense?: string) =>
    get<ArrestBreakdownRow[]>(
      `/api/v1/agency/${encodeURIComponent(ori)}/arrests?${qs({ category, offense })}`,
    ),
  agencyPoliceEmployment: (ori: string) =>
    get<PoliceEmploymentRow[]>(`/api/v1/agency/${encodeURIComponent(ori)}/police-employment`),
  agencyHateCrime: (ori: string, category?: string) =>
    get<ArrestRow[]>(`/api/v1/agency/${encodeURIComponent(ori)}/hate-crime?${qs({ category })}`),
  agencyShr: (ori: string, category?: string) =>
    get<ArrestRow[]>(`/api/v1/agency/${encodeURIComponent(ori)}/shr?${qs({ category })}`),
  agencyProperty: (ori: string, offense: string, category?: string) =>
    get<ArrestRow[]>(
      `/api/v1/agency/${encodeURIComponent(ori)}/property?${qs({ offense, category })}`,
    ),
  agencyNibrs: (ori: string, offense: string, category?: string) =>
    get<ArrestRow[]>(`/api/v1/agency/${encodeURIComponent(ori)}/nibrs?${qs({ offense, category })}`),
};
