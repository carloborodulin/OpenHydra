import { useMemo, useState } from "react";
import { Panel } from "../components/Panel";
import { PercentBarChart } from "../components/charts/PercentBarChart";
import type { ArrestRow } from "../lib/api";
import { usePopulation, useProperty } from "../lib/queries";
import { regionName } from "../lib/states";
import { BreakdownView } from "./BreakdownView";

const OFFENSES: { code: string; label: string }[] = [
  { code: "NB", label: "Burglary" },
  { code: "NL", label: "Larceny" },
  { code: "NMVT", label: "Motor Vehicle Theft" },
  { code: "NROB", label: "Robbery" },
];

// Dollar-total dimensions worth normalizing per resident (counts/averages are not).
const VALUE_CATS = new Set(["stolen_value", "recovered_value"]);

export function PropertyView({ region }: { region: string }) {
  const [offense, setOffense] = useState("NB");
  const [perCapita, setPerCapita] = useState(false);
  const level = region === "US" ? "national" : "state";
  // All dimensions for the chosen offense; BreakdownView derives the panels
  // (stolen/recovered value, location counts & average value — varies by offense).
  const query = useProperty(offense, undefined, level, region);

  // Latest Census population for the region — the per-capita denominator.
  const pop = usePopulation(level, region);
  const latestPop = useMemo(() => {
    const rows = pop.data ?? [];
    return rows.length ? rows[rows.length - 1].population : null;
  }, [pop.data]);

  // When per-capita is on, scale the dollar-total panels to "$ / resident".
  const transform = useMemo(() => {
    if (!perCapita || !latestPop) return undefined;
    return (rows: ArrestRow[]) =>
      rows.map((r) =>
        VALUE_CATS.has(r.category) && r.value != null
          ? { ...r, value: r.value / latestPop }
          : r,
      );
  }, [perCapita, latestPop]);

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
          {OFFENSES.map((o) => {
            const on = o.code === offense;
            return (
              <button
                key={o.code}
                type="button"
                onClick={() => setOffense(o.code)}
                className={`mono cursor-pointer border px-2.5 py-1 text-[0.62rem] tracking-wider uppercase transition ${
                  on
                    ? "glow border-accent bg-accent/10 text-accent"
                    : "border-line text-muted hover:border-line-strong hover:text-ink"
                }`}
              >
                {o.label}
              </button>
            );
          })}
        </div>
        <span className="h-4 w-px bg-line" />
        <button
          type="button"
          disabled={!latestPop}
          onClick={() => setPerCapita((v) => !v)}
          title={
            latestPop
              ? "Scale stolen/recovered $ to per-resident (Census population)"
              : "No population data for this region"
          }
          className={`mono cursor-pointer border px-2.5 py-1 text-[0.62rem] tracking-wider uppercase transition disabled:cursor-not-allowed disabled:opacity-40 ${
            perCapita
              ? "glow border-accent bg-accent/10 text-accent"
              : "border-line text-muted hover:border-line-strong hover:text-ink"
          }`}
        >
          Per Capita
        </button>
      </div>
      <BreakdownView
        region={region}
        query={query}
        transformRows={transform}
        extra={
          recovery.length ? (
            <Panel title={`Recovery Rate · By Property Type · ${regionName(region)}`} className="col-span-4">
              <PercentBarChart data={recovery} seriesName="Recovered" />
            </Panel>
          ) : null
        }
      />
    </>
  );
}
