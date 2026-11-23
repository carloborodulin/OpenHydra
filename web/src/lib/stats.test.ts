import { describe, expect, it } from "vitest";
import type { OffenseMonthly } from "./api";
import { annualRows } from "./stats";

const row = (period: string, offenses: number | null, cleared: number | null): OffenseMonthly => ({
  period,
  offenses_rate: null,
  offenses_actual: offenses,
  clearances_rate: null,
  clearances_actual: cleared,
  clearance_ratio: offenses && cleared != null ? cleared / offenses : null,
  ttm_rate: null,
  yoy_delta: null,
  index_2019: null,
});

describe("annualRows", () => {
  it("uses the ratio of sums, not the mean of monthly ratios", () => {
    // One busy month (100 reported, 50 cleared) and 11 quiet months (1 reported, 1 cleared).
    const rows = [row("2024-01-01", 100, 50)];
    for (let m = 2; m <= 12; m++) rows.push(row(`2024-${String(m).padStart(2, "0")}-01`, 1, 1));
    const [y] = annualRows(rows);
    expect(y.clearance).toBeCloseTo(61 / 111, 10); // 0.5495…, not the monthly mean 0.9583…
    expect(y.partial).toBe(false);
    expect(y.volume).toBe(111);
  });

  it("flags a year with fewer than 12 complete months", () => {
    const rows = [row("2024-01-01", 10, 5), row("2024-02-01", 10, null)];
    const [y] = annualRows(rows);
    expect(y.months).toBe(1);
    expect(y.partial).toBe(true);
    expect(y.clearance).toBe(0.5); // only the month with both counts
  });

  it("gives null clearance when no month reports both counts", () => {
    const [y] = annualRows([row("2023-05-01", null, 3)]);
    expect(y.clearance).toBeNull();
    expect(y.volume).toBeNull();
  });
});
