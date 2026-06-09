import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PoliceEmploymentRow } from "../../lib/api";
import { DarkTooltip } from "./DarkTooltip";

const TICK = { fill: "#5f7d92", fontSize: 10, fontFamily: "Share Tech Mono" };
const compact = (v: number) => Intl.NumberFormat("en", { notation: "compact" }).format(v);

// Collapse the long-format rows into one point per year with Officers (sworn)
// and Civilians totals (Male + Female). PE coverage is sparse, so years where
// both are null are dropped.
function toYearly(data: PoliceEmploymentRow[]) {
  const byYear = new Map<number, { Officers: number | null; Civilians: number | null }>();
  for (const r of data) {
    if (r.section !== "actual" || r.value == null) continue;
    const key = /Officers$/.test(r.metric) ? "Officers" : /Civilians$/.test(r.metric) ? "Civilians" : null;
    if (!key) continue;
    const slot = byYear.get(r.year) ?? { Officers: null, Civilians: null };
    slot[key] = (slot[key] ?? 0) + r.value;
    byYear.set(r.year, slot);
  }
  return [...byYear.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([year, v]) => ({ year: String(year), ...v }));
}

export function PoliceEmploymentChart({ data }: { data: PoliceEmploymentRow[] }) {
  const rows = toYearly(data);
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 6, right: 14, bottom: 0, left: -6 }}>
        <CartesianGrid stroke="rgba(34,211,238,0.08)" vertical={false} />
        <XAxis dataKey="year" tick={TICK} stroke="rgba(34,211,238,0.25)" />
        <YAxis tick={TICK} width={46} stroke="rgba(34,211,238,0.25)" tickFormatter={compact} />
        <Tooltip content={<DarkTooltip />} cursor={{ stroke: "rgba(34,211,238,0.3)" }} />
        <Legend wrapperStyle={{ fontFamily: "Share Tech Mono", fontSize: 10, color: "#5f7d92" }} />
        <Line
          type="monotone"
          dataKey="Officers"
          stroke="#22d3ee"
          strokeWidth={2}
          dot={false}
          connectNulls
          activeDot={{ r: 4, fill: "#22d3ee", stroke: "#04070d" }}
        />
        <Line
          type="monotone"
          dataKey="Civilians"
          stroke="#a78bfa"
          strokeWidth={2}
          dot={false}
          connectNulls
          activeDot={{ r: 4, fill: "#a78bfa", stroke: "#04070d" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
