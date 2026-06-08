import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ArrestRow } from "../../lib/api";
import { DarkTooltip } from "./DarkTooltip";

const TICK = { fill: "#5f7d92", fontSize: 10, fontFamily: "Share Tech Mono" };
const PALETTE = ["#22d3ee", "#3df5b0", "#a78bfa", "#f5b54a", "#ff5470", "#5f7d92"];

export function ArrestsChart({ data }: { data: ArrestRow[] }) {
  const rows = data
    .filter((d) => (d.value ?? 0) > 0)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, 6)
    .map((d) => ({ name: d.label, Arrests: d.value }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={rows} layout="vertical" margin={{ top: 2, right: 16, bottom: 2, left: 8 }}>
        <XAxis type="number" tick={TICK} stroke="rgba(45,212,238,0.25)" tickFormatter={(v: number) => Intl.NumberFormat("en", { notation: "compact" }).format(v)} />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ ...TICK, fontSize: 9 }}
          width={120}
          stroke="rgba(45,212,238,0.25)"
        />
        <Tooltip content={<DarkTooltip />} cursor={{ fill: "rgba(34,211,238,0.06)" }} />
        <Bar dataKey="Arrests" radius={[0, 2, 2, 0]} barSize={14}>
          {rows.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
