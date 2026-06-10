import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ArrestRow } from "../../lib/api";
import { useChartColors } from "../../lib/theme";
import { DarkTooltip } from "./DarkTooltip";

export function ArrestsChart({ data }: { data: ArrestRow[] }) {
  const c = useChartColors();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const rows = data
    .filter((d) => (d.value ?? 0) > 0)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, 6)
    .map((d) => ({ name: d.label, Arrests: d.value }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} layout="vertical" margin={{ top: 2, right: 16, bottom: 2, left: 8 }}>
        <XAxis type="number" tick={tick} stroke={c.axis} tickFormatter={(v: number) => Intl.NumberFormat("en", { notation: "compact" }).format(v)} />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ ...tick, fontSize: 9 }}
          width={120}
          stroke={c.axis}
        />
        <Tooltip content={<DarkTooltip />} cursor={{ fill: c.grid }} />
        <Bar dataKey="Arrests" radius={[0, 2, 2, 0]} barSize={14}>
          {rows.map((_, i) => (
            <Cell key={i} fill={c.palette[i % c.palette.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
