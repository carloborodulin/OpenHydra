import type { UseQueryResult } from "@tanstack/react-query";
import { useMemo } from "react";
import { Empty } from "../components/Empty";
import { Panel } from "../components/Panel";
import { ArrestsChart } from "../components/charts/ArrestsChart";
import type { ArrestRow } from "../lib/api";
import { regionName } from "../lib/states";

export interface Dimension {
  key: string; // the API `category` value (dimension name)
  label: string; // human-friendly panel title
}

// Shared layout for any "dimensional breakdown" domain (hate crime, SHR,
// expanded property, NIBRS): one fetch of all dimensions, grouped client-side
// into a grid of horizontal-bar panels.
export function BreakdownView({
  region,
  query,
  dimensions,
}: {
  region: string;
  query: UseQueryResult<ArrestRow[]>;
  dimensions: Dimension[];
}) {
  const byCategory = useMemo(() => {
    const m = new Map<string, ArrestRow[]>();
    for (const r of query.data ?? []) {
      const g = m.get(r.category) ?? [];
      g.push(r);
      m.set(r.category, g);
    }
    return m;
  }, [query.data]);
  const regionLabel = regionName(region);

  return (
    <main
      className="grid min-h-0 flex-1 grid-cols-12 gap-3 overflow-auto p-3"
      style={{ gridAutoRows: "minmax(240px, 1fr)" }}
    >
      {dimensions.map((d) => {
        const data = byCategory.get(d.key) ?? [];
        return (
          <Panel key={d.key} title={`${d.label} · ${regionLabel}`} className="col-span-4">
            {data.length ? <ArrestsChart data={data} /> : <Empty state={query} />}
          </Panel>
        );
      })}
    </main>
  );
}
