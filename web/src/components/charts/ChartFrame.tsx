import { type ReactNode, useRef } from "react";
import { ExportButtons } from "./ExportButtons";

const num = new Intl.NumberFormat("en-US", { maximumFractionDigits: 3 });

const heading = (key: string) =>
  key === "x" || key === "y" ? key.toUpperCase() : key[0].toUpperCase() + key.slice(1);

/**
 * A chart with a text equivalent: the chart has an accessible name, and a
 * "Data table" disclosure lists every row that the chart draws, with the same
 * keys. Screen-reader and keyboard users get the exact values.
 */
export function ChartFrame({
  label,
  rows,
  children,
}: {
  label: string;
  rows: Record<string, unknown>[];
  children: ReactNode;
}) {
  const columns = rows.length ? Object.keys(rows[0]) : [];
  const chart = useRef<HTMLDivElement>(null);
  return (
    <div className="flex h-full min-h-0 flex-col gap-1">
      <div ref={chart} className="min-h-0 flex-1" role="img" aria-label={label}>
        {children}
      </div>
      <div className="mono flex shrink-0 items-start gap-2 text-[0.6rem] text-muted">
        <details className="min-w-0 flex-1">
          <summary className="cursor-pointer select-none">Data table · {rows.length} rows</summary>
          <div className="mt-1 max-h-40 overflow-auto">
            <table className="w-full border-collapse text-left">
              <caption className="sr-only">{label}</caption>
              <thead>
                <tr>
                  {columns.map((c) => (
                    <th key={c} scope="col" className="py-0.5 pr-2 font-normal">
                      {heading(c)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} className="border-t border-line">
                    {columns.map((c) => {
                      const v = r[c];
                      return (
                        <td key={c} className="py-0.5 pr-2 text-ink tabular-nums">
                          {v == null ? "—" : typeof v === "number" ? num.format(v) : String(v)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
        <ExportButtons title={label} rows={rows} grain={columns[0]} chartRef={chart} />
      </div>
    </div>
  );
}
