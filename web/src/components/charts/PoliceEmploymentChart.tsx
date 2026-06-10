import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { PoliceEmploymentRow } from "../../lib/api";
import { useChartColors } from "../../lib/theme";
import { DarkTooltip } from "./DarkTooltip";

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
  const c = useChartColors();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const rows = toYearly(data);
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 6, right: 14, bottom: 0, left: -6 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="year" tick={tick} stroke={c.axis} />
        <YAxis tick={tick} width={46} stroke={c.axis} tickFormatter={compact} />
        <Tooltip content={<DarkTooltip />} cursor={{ stroke: c.axis }} />
        <Legend wrapperStyle={{ fontFamily: c.font, fontSize: 10, color: c.muted }} />
        <Line
          type="monotone"
          dataKey="Officers"
          stroke={c.accent}
          strokeWidth={2}
          dot={false}
          connectNulls
          activeDot={{ r: 4, fill: c.accent, stroke: c.bg }}
        />
        <Line
          type="monotone"
          dataKey="Civilians"
          stroke={c.violet}
          strokeWidth={2}
          dot={false}
          connectNulls
          activeDot={{ r: 4, fill: c.violet, stroke: c.bg }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
