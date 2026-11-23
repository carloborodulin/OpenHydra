import { useCallback, useMemo, useState } from "react";
import { Panel } from "../components/Panel";
import { PercentBarChart } from "../components/charts/PercentBarChart";
import type { ArrestRow } from "../lib/api";
import { dollars } from "../lib/measures";
import { perCapitaBasis, VALUE_CATS } from "../lib/perCapita";
import { useMeta, usePopulation, useProperty, usePropertyYears } from "../lib/queries";
import { regionName } from "../lib/states";
import { hudBtn } from "../lib/ui";
import { BreakdownView } from "./BreakdownView";

const OFFENSES: { code: string; label: string }[] = [
  { code: "NB", label: "Burglary" },
  { code: "NL", label: "Larceny" },
  { code: "NMVT", label: "Motor Vehicle Theft" },
  { code: "NROB", label: "Robbery" },
];

export function PropertyView({ region }: { region: string }) {
  const [offense, setOffense] = useState("NB");
  const [perCapita, setPerCapita] = useState(false);
  const [pickedYear, setYear] = useState<number | null>(null);
  const level = region === "US" ? "national" : "state";
  const snapshot = useMeta().data?.snapshot;

  // The years with data. An older snapshot has only window totals (no year).
  const yearsQ = usePropertyYears(offense, level, region);
  const years = useMemo(() => yearsQ.data?.years ?? [], [yearsQ.data]);
  const year = pickedYear != null && years.includes(pickedYear) ? pickedYear : (years.at(-1) ?? null);
  // All dimensions for the chosen offense and year; BreakdownView derives the
  // panels (stolen/recovered value, location counts and average value).
  const query = useProperty(offense, undefined, level, region, year ?? undefined);

  const pop = usePopulation(level, region);
  const windowLabel = snapshot
    ? `${(snapshot.window_from ?? "").slice(-4)}–${(snapshot.window_to ?? "").slice(-4)}`
    : "window";
  const basis = useMemo(
    () => perCapitaBasis(pop.data ?? [], year, windowLabel),
    [pop.data, year, windowLabel],
  );

  // When per-capita is on, scale the dollar-total panels to dollars per resident.
  const transform = useMemo(() => {
    const denominator = basis.population;
    if (!perCapita || !denominator) return undefined;
    return (rows: ArrestRow[]) =>
      rows.map((r) =>
        VALUE_CATS.has(r.category) && r.value != null ? { ...r, value: r.value / denominator } : r,
      );
  }, [perCapita, basis.population]);
  const measure = useCallback(
    (key: string) => (perCapita && basis.population && VALUE_CATS.has(key) ? dollars(basis.unit) : undefined),
    [perCapita, basis],
  );

  // Recovery rate by property type = recovered_value / stolen_value (both are
  // dimensions already in `query.data`; the FBI value table is the same regardless
  // of the offense slug, so this is offense-independent).
  const recovery = useMemo(() => {
    const rows = query.data ?? [];
    const stolen = new Map(
      rows.filter((r) => r.category === "stolen_value").map((r) => [r.label, r.value]),
    );
    const out: { label: string; value: number }[] = [];
    for (const r of rows.filter((r) => r.category === "recovered_value")) {
      const s = stolen.get(r.label);
      if (s != null && s > 0 && r.value != null) out.push({ label: r.label, value: (r.value / s) * 100 });
    }
    return out;
  }, [query.data]);

  return (
    <>
      <div className="mx-3 mt-3 flex flex-wrap items-center gap-2">
        <span className="panel-title shrink-0">Property Offense</span>
        <div className="flex flex-wrap gap-1.5">
          {OFFENSES.map((o) => (
            <button
              key={o.code}
              type="button"
              onClick={() => setOffense(o.code)}
              className={hudBtn(o.code === offense)}
            >
              {o.label}
            </button>
          ))}
        </div>
        <span className="hidden h-4 w-px bg-line lg:block" />
        {years.length > 0 && (
          <>
            <span className="hidden h-4 w-px bg-line lg:block" />
            <div className="flex flex-wrap gap-1.5" role="group" aria-label="Year">
              {years.map((y) => (
                <button
                  key={y}
                  type="button"
                  aria-pressed={y === year}
                  onClick={() => setYear(y)}
                  className={hudBtn(y === year)}
                >
                  {y}
                </button>
              ))}
            </div>
          </>
        )}
        <span className="hidden h-4 w-px bg-line lg:block" />
        <button
          type="button"
          disabled={!basis.population}
          aria-pressed={perCapita}
          onClick={() => setPerCapita((v) => !v)}
          title={
            basis.population
              ? `Show stolen and recovered value as ${basis.unit} (Census population)`
              : "No Census population for this area and year"
          }
          className={`${hudBtn(perCapita)} disabled:cursor-not-allowed disabled:opacity-40`}
        >
          Per Resident
        </button>
      </div>
      <p className="mono mx-3 mt-2 text-[0.62rem] text-muted">
        {year != null
          ? `Values for ${year}.`
          : `Values are totals for ${windowLabel} (this snapshot has no yearly split).`}
        {perCapita && basis.population ? ` Dollar panels: ${basis.unit}.` : ""}
        {!basis.population ? " No Census population for this area, so the per-resident view is off." : ""}
      </p>
      <BreakdownView
        domain="property"
        region={region}
        query={query}
        transformRows={transform}
        measure={measure}
        extra={
          recovery.length ? (
            <Panel
              title={`Recovery Rate · By Property Type · ${regionName(region)}`}
              className="col-span-1 lg:col-span-4"
            >
              <PercentBarChart data={recovery} seriesName="Recovered" />
            </Panel>
          ) : null
        }
      />
    </>
  );
}
