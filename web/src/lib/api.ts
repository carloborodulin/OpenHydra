export interface ArrestOffense {
  slug: string;
  code: string;
  name: string;
  category: string;
}

export interface Meta {
  offenses: string[];
  states: string[];
  levels: string[];
  // The full 48-code arrest taxonomy and the demographic categories present in
  // the warehouse (e.g. "Arrestee Race", "Arrestee Sex", "Male Arrests By Age").
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
}

export interface ArrestRow {
  category: string;
  label: string;
  value: number | null;
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

export interface PoliceEmploymentRow {
  section: string; // "rate" | "actual"
  metric: string;
  year: number;
  value: number | null;
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

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  return res.json() as Promise<T>;
}

const qs = (params: Record<string, string | undefined>) =>
  Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(v as string)}`)
    .join("&");

export const api = {
  meta: () => get<Meta>("/api/meta"),
  offensesMonthly: (offense: string, level = "national", area = "US") =>
    get<OffenseMonthly[]>(`/api/offenses/monthly?${qs({ offense, level, area })}`),
  arrests: (category: string, offense?: string, level = "national", area = "US") =>
    get<ArrestRow[]>(`/api/arrests?${qs({ level, area, offense, category })}`),
  agencies: (state?: string) => get<AgencyFeature[]>(`/api/agencies?${qs({ state })}`),
  policeEmployment: (level = "national", area = "US") =>
    get<PoliceEmploymentRow[]>(`/api/police-employment?${qs({ level, area })}`),
  // Hate crime breakdowns share the ArrestRow {category, label, value} shape;
  // `category` is the dimension (bias_category, offender_race, victim_type, …).
  hateCrime: (category?: string, level = "national", area = "US") =>
    get<ArrestRow[]>(`/api/hate-crime?${qs({ level, area, category })}`),
  // Expanded homicide (SHR); `category` is section_dimension (victim_age,
  // offense_weapons, offender_race, …).
  shr: (category?: string, level = "national", area = "US") =>
    get<ArrestRow[]>(`/api/shr?${qs({ level, area, category })}`),
  // Expanded property; `offense` is NB/NL/NMVT/NROB.
  property: (offense: string, category?: string, level = "national", area = "US") =>
    get<ArrestRow[]>(`/api/property?${qs({ level, area, offense, category })}`),
  // NIBRS incidents; `offense` is a NIBRS code (e.g. 13A).
  nibrs: (offense: string, category?: string, level = "national", area = "US") =>
    get<ArrestRow[]>(`/api/nibrs?${qs({ level, area, offense, category })}`),
  // LESDC (LE suicide data collection); national only, by year + chart type.
  lesdc: (chartType: string, year: number, section?: string) =>
    get<LesdcRow[]>(`/api/lesdc?${qs({ chart_type: chartType, year: String(year), section })}`),
  // Use of Force; national only.
  uofParticipation: () => get<UofParticipationRow[]>("/api/uof/participation"),
  uofQuestions: (year: number, category?: string) =>
    get<ArrestRow[]>(`/api/uof/questions?${qs({ year: String(year), category })}`),
  // NIBRS estimations; national / region, numeric offense code.
  nibrsEstimation: (level: string, area: string, offense: string, category?: string) =>
    get<ArrestRow[]>(`/api/nibrs-estimation?${qs({ level, area, offense, category })}`),

  // Agency drill-down: served live from the CDE API by the backend, same shapes.
  agencyOffenses: (ori: string, offense: string) =>
    get<OffenseMonthly[]>(`/api/agency/${encodeURIComponent(ori)}/offenses?${qs({ offense })}`),
  agencyArrests: (ori: string, category: string, offense?: string) =>
    get<ArrestRow[]>(
      `/api/agency/${encodeURIComponent(ori)}/arrests?${qs({ category, offense })}`,
    ),
  agencyPoliceEmployment: (ori: string) =>
    get<PoliceEmploymentRow[]>(`/api/agency/${encodeURIComponent(ori)}/police-employment`),
  agencyHateCrime: (ori: string, category?: string) =>
    get<ArrestRow[]>(`/api/agency/${encodeURIComponent(ori)}/hate-crime?${qs({ category })}`),
  agencyShr: (ori: string, category?: string) =>
    get<ArrestRow[]>(`/api/agency/${encodeURIComponent(ori)}/shr?${qs({ category })}`),
  agencyProperty: (ori: string, offense: string, category?: string) =>
    get<ArrestRow[]>(`/api/agency/${encodeURIComponent(ori)}/property?${qs({ offense, category })}`),
  agencyNibrs: (ori: string, offense: string, category?: string) =>
    get<ArrestRow[]>(`/api/agency/${encodeURIComponent(ori)}/nibrs?${qs({ offense, category })}`),
};
