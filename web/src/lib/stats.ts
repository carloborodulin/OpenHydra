import type { OffenseMonthly } from "./api";

/** One year of the performance view. */
export interface AnnualRow {
  year: number;
  /** Offenses reported in the year (sum over the months that report a count). */
  volume: number | null;
  /**
   * Annual clearance rate: cleared ÷ reported, both summed over the months that
   * report both counts. A ratio of sums, so a quiet month does not weigh as
   * much as a busy one (the mean of monthly ratios did).
   */
  clearance: number | null;
  /** Months with both counts. Fewer than 12 marks a partial year. */
  months: number;
  partial: boolean;
}

export function annualRows(rows: OffenseMonthly[]): AnnualRow[] {
  const acc = new Map<number, { vol: number; volMonths: number; cleared: number; reported: number; months: number }>();
  for (const r of rows) {
    const year = Number(r.period.slice(0, 4));
    const a = acc.get(year) ?? { vol: 0, volMonths: 0, cleared: 0, reported: 0, months: 0 };
    if (r.offenses_actual != null) {
      a.vol += r.offenses_actual;
      a.volMonths += 1;
    }
    if (r.offenses_actual != null && r.clearances_actual != null) {
      a.cleared += r.clearances_actual;
      a.reported += r.offenses_actual;
      a.months += 1;
    }
    acc.set(year, a);
  }
  return [...acc.entries()]
    .sort(([x], [y]) => x - y)
    .map(([year, a]) => ({
      year,
      volume: a.volMonths ? a.vol : null,
      clearance: a.reported > 0 ? a.cleared / a.reported : null,
      months: a.months,
      partial: a.months < 12 || a.volMonths < 12,
    }));
}
