import { useMemo } from "react";
import { Empty } from "../components/Empty";
import { Panel } from "../components/Panel";
import { StatTile } from "../components/StatTile";
import { ClearanceChart } from "../components/charts/ClearanceChart";
import {
  NibrsAdoptionChart,
  type PerfYear,
  StaffingClearanceScatter,
  VolumeClearanceChart,
} from "../components/charts/PerformanceChart";
import { fmtNum, fmtPct, fmtRate, titleCase } from "../lib/format";
import { useAgencies, useOffenseMonthly, usePoliceEmployment } from "../lib/queries";
import { regionName } from "../lib/states";

// Last row whose `key` is non-null (rows are year-ascending).
function lastBy(rows: PerfYear[], key: keyof PerfYear): PerfYear | null {
  for (let i = rows.length - 1; i >= 0; i--) if (rows[i][key] != null) return rows[i];
  return null;
}

// Correlate crime volume, clearance rate, and officer staffing per 1,000 people.
// Volume + clearance come from fct_offenses_monthly (aggregated to years); staffing
// is the per-capita "rate" section of fct_police_employment.
export function PerformanceView({ offense, region }: { offense: string; region: string }) {
  const isNational = region === "US";
  const level = isNational ? "national" : "state";
  const area = region;
  const regionLabel = regionName(region);

  const monthly = useOffenseMonthly(offense, level, area);
  const pe = usePoliceEmployment(level, area);
  const agencies = useAgencies(isNational ? undefined : region);
  const rows = useMemo(() => monthly.data ?? [], [monthly.data]);

  // Cumulative share of agencies reporting via NIBRS, by year (reporting integrity).
  const adoption = useMemo(() => {
    const ags = agencies.data ?? [];
    if (!ags.length) return [];
    const out: { year: number; pct: number }[] = [];
    for (let y = 2015; y <= 2024; y++) {
      const n = ags.filter((a) => a.nibrs_start_year != null && a.nibrs_start_year <= y).length;
      out.push({ year: y, pct: (n / ags.length) * 100 });
    }
    return out;
  }, [agencies.data]);

  const perf = useMemo<PerfYear[]>(() => {
    const vol = new Map<number, number>();
    const clrSum = new Map<number, number>();
    const clrCnt = new Map<number, number>();
    for (const r of rows) {
      const y = Number(r.period.slice(0, 4));
      if (r.offenses_actual != null) vol.set(y, (vol.get(y) ?? 0) + r.offenses_actual);
      if (r.clearance_ratio != null) {
        clrSum.set(y, (clrSum.get(y) ?? 0) + r.clearance_ratio);
        clrCnt.set(y, (clrCnt.get(y) ?? 0) + 1);
      }
    }
    const staff = new Map<number, number>();
    for (const p of pe.data ?? []) {
      if (p.section === "rate" && p.value != null && /per 1,000/i.test(p.metric)) {
        staff.set(p.year, p.value);
      }
    }
    const years = [...new Set([...vol.keys(), ...staff.keys()])].sort((a, b) => a - b);
    return years.map((year) => ({
      year,
      volume: vol.get(year) ?? null,
      clearance: clrCnt.get(year) ? (clrSum.get(year) as number) / (clrCnt.get(year) as number) : null,
      staffing: staff.get(year) ?? null,
    }));
  }, [rows, pe.data]);

  const latestStaff = lastBy(perf, "staffing");
  const latestClr = lastBy(perf, "clearance");
  const latestVol = lastBy(perf, "volume");
  const peakVol = perf.reduce<PerfYear | null>(
    (best, r) => (r.volume != null && (!best || r.volume > (best.volume as number)) ? r : best),
    null,
  );

  return (
    <main className="grid flex-1 grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:min-h-0 lg:grid-cols-12 lg:[grid-template-rows:auto_minmax(0,1fr)_minmax(0,1fr)]">
      <div className="col-span-1 lg:col-span-3">
        <StatTile
          label="Staffing /1k"
          value={fmtRate(latestStaff?.staffing)}
          sub={latestStaff ? `${latestStaff.year} · LE employees / 1,000` : "—"}
        />
      </div>
      <div className="col-span-1 lg:col-span-3">
        <StatTile
          label="Clearance"
          accent="warn"
          value={fmtPct(latestClr?.clearance)}
          sub={latestClr ? `${latestClr.year} · ${titleCase(offense)}` : "—"}
        />
      </div>
      <div className="col-span-1 lg:col-span-3">
        <StatTile
          label="Annual Volume"
          accent="alert"
          value={fmtNum(latestVol?.volume)}
          sub={latestVol ? `${latestVol.year} · reported` : "—"}
        />
      </div>
      <div className="col-span-1 lg:col-span-3">
        <StatTile
          label="Peak Volume"
          accent="good"
          value={fmtNum(peakVol?.volume)}
          sub={peakVol ? `${peakVol.year}` : "—"}
        />
      </div>

      <Panel
        title={`Volume vs Clearance · ${titleCase(offense)} · ${regionLabel}`}
        className="col-span-full lg:col-span-8 lg:col-start-1 lg:row-start-2"
      >
        {perf.length ? <VolumeClearanceChart data={perf} /> : <Empty state={monthly} />}
      </Panel>

      <Panel
        title={`Staffing vs Clearance · ${regionLabel}`}
        className="col-span-full lg:col-span-4 lg:col-start-9 lg:row-start-2"
      >
        {perf.some((p) => p.staffing != null && p.clearance != null) ? (
          <StaffingClearanceScatter data={perf} />
        ) : (
          <Empty state={pe} />
        )}
      </Panel>

      <Panel
        title={`Clearance Ratio · ${titleCase(offense)} · ${regionLabel}`}
        className="col-span-full lg:col-span-8 lg:col-start-1 lg:row-start-3"
      >
        {rows.length ? <ClearanceChart data={rows} /> : <Empty state={monthly} />}
      </Panel>

      <Panel
        title={`NIBRS Adoption · ${regionLabel}`}
        className="col-span-full lg:col-span-4 lg:col-start-9 lg:row-start-3"
      >
        {adoption.length ? <NibrsAdoptionChart data={adoption} /> : <Empty state={agencies} />}
      </Panel>
    </main>
  );
}
