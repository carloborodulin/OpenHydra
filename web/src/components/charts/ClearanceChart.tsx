import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { OffenseMonthly } from "../../lib/api";
import { monthLabel } from "../../lib/format";
import { DarkTooltip } from "./DarkTooltip";

const TICK = { fill: "#5f7d92", fontSize: 10, fontFamily: "Share Tech Mono" };

export function ClearanceChart({ data }: { data: OffenseMonthly[] }) {
  const rows = data
    .filter((d) => d.clearance_ratio != null)
    .map((d) => ({ period: monthLabel(d.period), Cleared: d.clearance_ratio }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 6, right: 14, bottom: 0, left: -10 }}>
        <CartesianGrid stroke="rgba(245,181,74,0.08)" vertical={false} />
        <XAxis dataKey="period" tick={TICK} minTickGap={48} stroke="rgba(245,181,74,0.25)" />
        <YAxis
          tick={TICK}
          width={42}
          stroke="rgba(245,181,74,0.25)"
          tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
        />
        <Tooltip content={<DarkTooltip percent />} cursor={{ stroke: "rgba(245,181,74,0.3)" }} />
        <Line
          type="monotone"
          dataKey="Cleared"
          stroke="#f5b54a"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: "#f5b54a", stroke: "#04070d" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
