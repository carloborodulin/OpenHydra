import { useMemo, useState } from "react";
import { Empty } from "../components/Empty";
import { Panel } from "../components/Panel";
import { Select } from "../components/Select";
import { ArrestsChart } from "../components/charts/ArrestsChart";
import type { ArrestRow } from "../lib/api";
import { useLesdc } from "../lib/queries";
import { hudBtn } from "../lib/ui";

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
      <div className="mx-3 mt-3 flex flex-col items-stretch gap-3 lg:flex-row lg:flex-wrap lg:items-center">
        <div className="flex flex-wrap items-center gap-3">
          <span className="panel-title shrink-0">LE Suicide Data</span>
          <div className="flex flex-wrap gap-1.5">
            {YEARS.map((y) => (
              <button key={y} type="button" onClick={() => setYear(y)} className={hudBtn(y === year)}>
                {y}
              </button>
            ))}
          </div>
        </div>
        <span className="hidden h-4 w-px bg-line lg:block" />
        <Select
          value={chartType}
          onChange={setChartType}
          options={CHART_TYPES.map((c) => ({ value: c.code, label: c.label }))}
          title="LESDC chart type"
          className="w-full lg:w-56"
        />
      </div>

      <main className="grid flex-1 grid-cols-1 gap-3 p-3 [grid-auto-rows:minmax(280px,auto)] sm:grid-cols-2 lg:min-h-0 lg:grid-cols-12 lg:overflow-auto lg:[grid-auto-rows:minmax(280px,1fr)]">
        <Panel title={`Suicides · ${label} · ${year}`} className="col-span-1 lg:col-span-6">
          {suicide.length ? <ArrestsChart data={suicide} /> : <Empty state={query} />}
        </Panel>
        <Panel title={`Attempted · ${label} · ${year}`} className="col-span-1 lg:col-span-6">
          {attempted.length ? <ArrestsChart data={attempted} /> : <Empty state={query} />}
        </Panel>
      </main>
    </>
  );
}
