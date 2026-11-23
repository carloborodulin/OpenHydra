import type { Snapshot } from "./api";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "01-2015" -> "Jan 2015"; "2015" -> "2015". No timezone conversion. */
export function fmtPeriod(value: string | null | undefined): string {
  if (!value) return "?";
  const m = /^(\d{2})-(\d{4})$/.exec(value);
  return m ? `${MONTHS[Number(m[1]) - 1]} ${m[2]}` : value;
}

export function fmtWindow(from: string | null | undefined, to: string | null | undefined): string {
  return `${fmtPeriod(from)} – ${fmtPeriod(to)}`;
}

/**
 * The calendar date of an ISO timestamp, as written (UTC). Slicing the string,
 * not new Date(), keeps the date the same in every browser timezone.
 */
export function fmtDay(iso: string | null | undefined): string {
  return iso ? iso.slice(0, 10) : "?";
}

/** The release files that each view reads, for its coverage line. */
export const VIEW_DOMAINS: Record<string, string[]> = {
  overview: ["summarized", "arrests", "pe", "agencies"],
  performance: ["summarized", "pe", "agencies"],
  "hate-crime": ["hate_crime"],
  homicide: ["shr"],
  property: ["property"],
  nibrs: ["nibrs", "agencies"],
  "nibrs-estimation": ["nibrs_estimation"],
  "use-of-force": ["uof_participation", "uof_questions"],
  lesdc: ["lesdc"],
};

/** The coverage of the files a view reads: window and extraction date(s). */
export function viewCoverage(snapshot: Snapshot, view: string) {
  const names = VIEW_DOMAINS[view] ?? [];
  const domains = snapshot.domains.filter((d) => names.includes(d.domain) && d.window_from);
  const windows = [...new Set(domains.map((d) => fmtWindow(d.window_from, d.window_to)))];
  const days = [...new Set(snapshot.domains.filter((d) => names.includes(d.domain)).map((d) => fmtDay(d.extracted_at)))].sort();
  return { windows, days };
}
