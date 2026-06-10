import { useMemo, useState } from "react";
import { Empty } from "../components/Empty";
import { Panel } from "../components/Panel";
import { ArrestsChart } from "../components/charts/ArrestsChart";
import type { ArrestRow } from "../lib/api";
import { useLesdc } from "../lib/queries";

// Mirrors cdeclient LESDC_CHART_TYPES.
const CHART_TYPES: { code: string; label: string }[] = [
  { code: "totals", label: "Totals" },
  { code: "demographics", label: "Demographics" },
  { code: "race", label: "Race / Ethnicity" },
  { code: "manner", label: "Manner of Death" },
  { code: "location", label: "Location" },
  { code: "employment", label: "Employment Status" },
  { code: "occupation", label: "Occupation" },
  { code: "military", label: "Military Service" },
  { code: "duty", label: "Duty Status" },
  { code: "experience", label: "Years of Service" },
  { code: "exp", label: "Exposure" },
  { code: "expfollowing", label: "Exposure (Following)" },
  { code: "suffered", label: "Suffered" },
  { code: "prior", label: "Prior Indicators" },
  { code: "investigation", label: "Investigation" },
  { code: "wellness", label: "Agency Wellness Programs" },
];
const YEARS = [2023, 2022];
const SELECT =
  "mono max-w-[14rem] cursor-pointer border border-line bg-[rgba(34,211,238,0.06)] px-2 py-1 text-[0.62rem] tracking-wider text-accent uppercase transition hover:border-line-strong focus:border-accent focus:outline-none";

export function LesdcView() {
  const [year, setYear] = useState(2023);
  const [chartType, setChartType] = useState("manner");
  const query = useLesdc(chartType, year);
  const label = CHART_TYPES.find((c) => c.code === chartType)?.label ?? chartType;

  // Split into Suicide (S) / Attempted Suicide (AS) and shape for ArrestsChart.
  const [suicide, attempted] = useMemo(() => {
    const toRows = (section: string): ArrestRow[] =>
      (query.data ?? [])
        .filter((r) => r.section === section)
        .map((r) => ({ category: section, label: r.label, value: r.value }));
    return [toRows("S"), toRows("AS")];
  }, [query.data]);

  return (
    <>
      <div className="mx-3 mt-3 flex flex-wrap items-center gap-3">
        <span className="panel-title shrink-0">LE Suicide Data</span>
        <div className="flex gap-1.5">
          {YEARS.map((y) => {
            const on = y === year;
            return (
              <button
                key={y}
                type="button"
                onClick={() => setYear(y)}
                className={`mono cursor-pointer border px-2.5 py-1 text-[0.62rem] tracking-wider uppercase transition ${
                  on
                    ? "glow border-accent bg-[rgba(34,211,238,0.1)] text-accent"
                    : "border-line text-muted hover:border-line-strong hover:text-ink"
                }`}
              >
                {y}
              </button>
            );
          })}
        </div>
        <span className="h-4 w-px bg-line" />
        <select
          value={chartType}
          onChange={(e) => setChartType(e.target.value)}
          className={SELECT}
          title="LESDC chart type"
        >
          {CHART_TYPES.map((c) => (
            <option key={c.code} value={c.code}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <main
        className="grid min-h-0 flex-1 grid-cols-12 gap-3 overflow-auto p-3"
        style={{ gridAutoRows: "minmax(280px, 1fr)" }}
      >
        <Panel title={`Suicides · ${label} · ${year}`} className="col-span-6">
          {suicide.length ? <ArrestsChart data={suicide} /> : <Empty state={query} />}
        </Panel>
        <Panel title={`Attempted · ${label} · ${year}`} className="col-span-6">
          {attempted.length ? <ArrestsChart data={attempted} /> : <Empty state={query} />}
        </Panel>
      </main>
    </>
  );
}
