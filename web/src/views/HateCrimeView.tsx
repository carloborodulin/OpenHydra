import { useMemo } from "react";
import { Empty } from "../components/Empty";
import { Panel } from "../components/Panel";
import { ArrestsChart } from "../components/charts/ArrestsChart";
import type { ArrestRow } from "../lib/api";
import { useHateCrime } from "../lib/queries";
import { regionName } from "../lib/states";

// Curated breakdown dimensions to surface as panels (the API returns more —
// judicial_district, offender_ethnicity — which can be added later).
const DIMENSIONS: { key: string; label: string }[] = [
  { key: "bias_category", label: "Bias Category" },
  { key: "bias", label: "Bias Motivation" },
  { key: "offender_race", label: "Offender Race" },
  { key: "victim_type", label: "Victim Type" },
  { key: "location_type", label: "Location Type" },
  { key: "offense_type", label: "Offense Type" },
];

export function HateCrimeView({ region }: { region: string }) {
  const level = region === "US" ? "national" : "state";
  // One fetch returns every dimension; group client-side into per-panel rows.
  const hc = useHateCrime(undefined, level, region);
  const byCategory = useMemo(() => {
    const m = new Map<string, ArrestRow[]>();
    for (const r of hc.data ?? []) {
      const g = m.get(r.category) ?? [];
      g.push(r);
      m.set(r.category, g);
    }
    return m;
  }, [hc.data]);
  const regionLabel = regionName(region);

  return (
    <main
      className="grid min-h-0 flex-1 grid-cols-12 gap-3 overflow-auto p-3"
      style={{ gridAutoRows: "minmax(240px, 1fr)" }}
    >
      {DIMENSIONS.map((d) => {
        const data = byCategory.get(d.key) ?? [];
        return (
          <Panel key={d.key} title={`${d.label} · ${regionLabel}`} className="col-span-4">
            {data.length ? <ArrestsChart data={data} /> : <Empty state={hc} />}
          </Panel>
        );
      })}
    </main>
  );
}
