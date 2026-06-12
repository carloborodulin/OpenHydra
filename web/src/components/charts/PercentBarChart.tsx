import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useChartColors } from "../../lib/theme";
import { DarkTooltip } from "./DarkTooltip";

// Horizontal bar of percentage values (top 6, descending) — e.g. recovery rate by
// property type. Like ArrestsChart but axis/tooltip read as percents.
export function PercentBarChart({
  data,
  seriesName = "Rate",
}: {
  data: { label: string; value: number | null }[];
  seriesName?: string;
}) {
  const c = useChartColors();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const rows = data
    .filter((d) => (d.value ?? 0) > 0)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, 6)
    .map((d) => ({ name: d.label, [seriesName]: d.value == null ? null : +d.value.toFixed(1) }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} layout="vertical" margin={{ top: 2, right: 16, bottom: 2, left: 8 }}>
        <XAxis
          type="number"
          tick={tick}
          stroke={c.axis}
          tickFormatter={(v: number) => `${v}%`}
        />
        <YAxis type="category" dataKey="name" tick={{ ...tick, fontSize: 9 }} width={120} stroke={c.axis} />
        <Tooltip content={<DarkTooltip unit="%" />} cursor={{ fill: c.grid }} />
        <Bar dataKey={seriesName} radius={[0, 2, 2, 0]} barSize={14}>
          {rows.map((_, i) => (
            <Cell key={i} fill={c.palette[i % c.palette.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
