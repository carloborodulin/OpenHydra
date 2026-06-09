export interface Meta {
  offenses: string[];
  states: string[];
  levels: string[];
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

  // Agency drill-down: served live from the CDE API by the backend, same shapes.
  agencyOffenses: (ori: string, offense: string) =>
    get<OffenseMonthly[]>(`/api/agency/${encodeURIComponent(ori)}/offenses?${qs({ offense })}`),
  agencyArrests: (ori: string, category: string, offense?: string) =>
    get<ArrestRow[]>(
      `/api/agency/${encodeURIComponent(ori)}/arrests?${qs({ category, offense })}`,
    ),
  agencyPoliceEmployment: (ori: string) =>
    get<PoliceEmploymentRow[]>(`/api/agency/${encodeURIComponent(ori)}/police-employment`),
};
