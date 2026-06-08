import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { OffenseMonthly } from "../../lib/api";
import { monthLabel } from "../../lib/format";
import { DarkTooltip } from "./DarkTooltip";

const TICK = { fill: "#5f7d92", fontSize: 10, fontFamily: "Share Tech Mono" };

export function TrendChart({ data }: { data: OffenseMonthly[] }) {
  const rows = data.map((d) => ({ period: monthLabel(d.period), Rate: d.offenses_rate }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={rows} margin={{ top: 6, right: 14, bottom: 0, left: -10 }}>
        <defs>
          <linearGradient id="g-rate" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.5} />
            <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="rgba(45,212,238,0.08)" vertical={false} />
        <XAxis dataKey="period" tick={TICK} minTickGap={48} stroke="rgba(45,212,238,0.25)" />
        <YAxis tick={TICK} width={42} stroke="rgba(45,212,238,0.25)" />
        <Tooltip content={<DarkTooltip unit=" /100k" />} cursor={{ stroke: "rgba(34,211,238,0.3)" }} />
        <Area
          type="monotone"
          dataKey="Rate"
          stroke="#22d3ee"
          strokeWidth={2}
          fill="url(#g-rate)"
          dot={false}
          activeDot={{ r: 4, fill: "#22d3ee", stroke: "#04070d" }}
          isAnimationActive
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
