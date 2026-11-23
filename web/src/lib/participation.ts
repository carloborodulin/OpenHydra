import type { UofParticipationRow } from "./api";
const full = new Intl.NumberFormat("en-US");
const fmtFull = (v: number) => full.format(v);

/**
 * The two participation measures of the FBI Use-of-Force collection. They have
 * different denominators, so the dashboard shows them apart:
 *
 * - `participation_percent` is the FBI's own figure. The FBI states coverage
 *   as the share of sworn officers that the participating agencies employ.
 * - The agency share is participating agencies ÷ all agencies.
 *
 * For 2022 the FBI figure is 75% while 10,353 of 18,514 agencies is 55.9%.
 */
export interface ParticipationFacts {
  fbiPercent: string; // "75%" or "—" when the FBI value is null
  agencyShare: string; // "55.9%" or "—"
  agencyLine: string; // "10,353 of 18,514 agencies"
}

export function participationFacts(p: UofParticipationRow): ParticipationFacts {
  const fbi = p.participation_percent;
  const share =
    p.participating_agencies != null && p.total_agencies
      ? (p.participating_agencies / p.total_agencies) * 100
      : null;
  return {
    fbiPercent: fbi == null ? "—" : `${Math.round(fbi)}%`,
    agencyShare: share == null ? "—" : `${share.toFixed(1)}%`,
    agencyLine:
      p.participating_agencies == null || p.total_agencies == null
        ? "agency counts not reported"
        : `${fmtFull(p.participating_agencies)} of ${fmtFull(p.total_agencies)} agencies`,
  };
}
