import type { AgencyFeature } from "./api";

export const MAX_RESULTS = 20;

/** Agencies whose name, ORI or county contains every word of the query. */
export function searchAgencies(agencies: AgencyFeature[], query: string): AgencyFeature[] {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean);
  if (!words.length) return [];
  const out: AgencyFeature[] = [];
  for (const a of agencies) {
    const hay =
      `${a.agency_name ?? ""} ${a.ori} ${a.county ?? ""} ${a.state_abbr ?? ""}`.toLowerCase();
    if (words.every((w) => hay.includes(w))) {
      out.push(a);
      if (out.length === MAX_RESULTS) break;
    }
  }
  return out;
}

