import type { UseQueryResult } from "@tanstack/react-query";
import { type ReactNode, useMemo } from "react";
import { Empty } from "../components/Empty";
import { Panel } from "../components/Panel";
import { ArrestsChart } from "../components/charts/ArrestsChart";
import type { ArrestRow } from "../lib/api";
import { regionName } from "../lib/states";

export interface Dimension {
  key: string; // the API `category` value (dimension name)
  label: string; // human-friendly panel title
}

// snake_case / kebab-case -> Title Case (for derived dimension labels).
const prettify = (key: string): string =>
  key
    .split(/[_-]/)
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");

// Shared layout for any "dimensional breakdown" domain (hate crime, SHR,
// expanded property, NIBRS): one fetch of all dimensions, grouped client-side
// into a grid of horizontal-bar panels. Pass `dimensions` for a curated set +
// labels, or omit it to render every dimension present in the data.
export function BreakdownView({
  region,
  query,
  dimensions,
  extra,
  transformRows,
}: {
  region: string;
  query: UseQueryResult<ArrestRow[]>;
  dimensions?: Dimension[];
  // Optional extra panel(s) appended to the grid (e.g. a derived ratio panel).
  extra?: ReactNode;
  // Optional transform applied to the rows before grouping (e.g. per-capita scaling).
  transformRows?: (rows: ArrestRow[]) => ArrestRow[];
}) {
  const byCategory = useMemo(() => {
    const src = transformRows ? transformRows(query.data ?? []) : (query.data ?? []);
    const m = new Map<string, ArrestRow[]>();
    for (const r of src) {
      const g = m.get(r.category) ?? [];
      g.push(r);
      m.set(r.category, g);
    }
    return m;
  }, [query.data, transformRows]);

  const dims = useMemo<Dimension[]>(
    () => dimensions ?? [...byCategory.keys()].sort().map((k) => ({ key: k, label: prettify(k) })),
    [dimensions, byCategory],
  );
  const regionLabel = regionName(region);

  // No dimensions yet (loading / no data) — show a single placeholder.
  if (!dims.length) {
    return (
      <main className="flex min-h-[20rem] flex-1 p-3 lg:min-h-0">
        <div className="panel brackets enter flex-1">
          <Empty state={query} />
        </div>
      </main>
    );
  }

  return (
    <main className="grid flex-1 grid-cols-1 gap-3 p-3 [grid-auto-rows:minmax(240px,auto)] sm:grid-cols-2 lg:min-h-0 lg:grid-cols-12 lg:overflow-auto lg:[grid-auto-rows:minmax(240px,1fr)]">
      {dims.map((d) => {
        const data = byCategory.get(d.key) ?? [];
        return (
          <Panel
            key={d.key}
            title={`${d.label} · ${regionLabel}`}
            className="col-span-1 lg:col-span-4"
          >
            {data.length ? <ArrestsChart data={data} /> : <Empty state={query} />}
          </Panel>
        );
      })}
      {extra}
    </main>
  );
}
