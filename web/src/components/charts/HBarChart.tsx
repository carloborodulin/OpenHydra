import { ANIMATE } from "../../lib/motion";
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ArrestRow } from "../../lib/api";
import type { Measure } from "../../lib/measures";
import { useChartColors } from "../../lib/theme";
import { useIsMobile } from "../../lib/useMediaQuery";

interface TipProps {
  active?: boolean;
  payload?: { value?: number; color?: string; payload?: { name: string } }[];
  measure: Measure;
}

function Tip({ active, payload, measure }: TipProps) {
  const p = payload?.[0];
  if (!active || !p || typeof p.value !== "number") return null;
  return (
    <div className="panel mono px-3 py-2 text-[0.7rem]">
      <div className="mb-1 text-accent">{p.payload?.name}</div>
      <div className="text-ink">
        {measure.name}: <span style={{ color: p.color }}>{measure.format(p.value)}</span>
      </div>
    </div>
  );
}

/**
 * Horizontal bars for one breakdown dimension. The chart shows the largest
 * `limit` positive values and says so. The table below it lists every
 * category, zeros and unknowns included, for screen readers and exact values.
 */
export function HBarChart({
  data,
  measure,
  limit = 6,
  label,
}: {
  data: ArrestRow[];
  measure: Measure;
  limit?: number;
  /** A short description of the chart for assistive technology. */
  label?: string;
}) {
  const c = useChartColors();
  const mobile = useIsMobile();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const sorted = [...data].sort((a, b) => (b.value ?? -1) - (a.value ?? -1));
  const positive = sorted.filter((d) => (d.value ?? 0) > 0);
  const rows = positive.slice(0, limit).map((d) => ({ name: d.label, value: d.value as number }));
  const shownNote =
    positive.length > rows.length
      ? `Top ${rows.length} of ${sorted.length} categories`
      : `${sorted.length} categories`;

  return (
    <div className="flex h-full min-h-0 flex-col gap-1">
      <div
        className="min-h-0 flex-1"
        role="img"
        aria-label={`${label ?? measure.name}: ${shownNote}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={rows}
            layout="vertical"
            margin={{ top: 2, right: 16, bottom: 2, left: 8 }}
          >
            <XAxis type="number" tick={tick} stroke={c.axis} tickFormatter={measure.axis} />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ ...tick, fontSize: mobile ? 8 : 9 }}
              width={mobile ? 78 : 120}
              stroke={c.axis}
              tickFormatter={
                mobile ? (v: string) => (v.length > 12 ? `${v.slice(0, 11)}…` : v) : undefined
              }
            />
            <Tooltip content={<Tip measure={measure} />} cursor={{ fill: c.grid }} />
            <Bar
              isAnimationActive={ANIMATE}
              dataKey="value"
              name={measure.name}
              radius={[0, 2, 2, 0]}
              barSize={14}
            >
              {rows.map((_, i) => (
                <Cell key={i} fill={c.palette[i % c.palette.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="mono shrink-0 text-[0.6rem] text-muted">
        <summary className="cursor-pointer select-none">
          {shownNote} · {measure.name} · table
        </summary>
        <div className="mt-1 max-h-40 overflow-auto">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">{label ?? measure.name}</caption>
            <thead>
              <tr>
                <th scope="col" className="py-0.5 pr-2 font-normal">
                  Category
                </th>
                <th scope="col" className="py-0.5 text-right font-normal">
                  {measure.name}
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((d) => (
                <tr key={d.label} className="border-t border-line">
                  <td className="py-0.5 pr-2 text-ink">{d.label}</td>
                  <td className="py-0.5 text-right text-ink tabular-nums">
                    {d.value == null ? "—" : measure.format(d.value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
