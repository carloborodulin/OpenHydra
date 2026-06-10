import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { OffenseMonthly } from "../../lib/api";
import { monthLabel } from "../../lib/format";
import { useChartColors } from "../../lib/theme";
import { DarkTooltip } from "./DarkTooltip";

export function TrendChart({ data }: { data: OffenseMonthly[] }) {
  const c = useChartColors();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const rows = data.map((d) => ({ period: monthLabel(d.period), Rate: d.offenses_rate }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={rows} margin={{ top: 6, right: 14, bottom: 0, left: -10 }}>
        <defs>
          <linearGradient id="g-rate" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={c.accent} stopOpacity={0.5} />
            <stop offset="100%" stopColor={c.accent} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="period" tick={tick} minTickGap={48} stroke={c.axis} />
        <YAxis tick={tick} width={42} stroke={c.axis} />
        <Tooltip content={<DarkTooltip unit=" /100k" />} cursor={{ stroke: c.axis }} />
        <Area
          type="monotone"
          dataKey="Rate"
          stroke={c.accent}
          strokeWidth={2}
          fill="url(#g-rate)"
          dot={false}
          activeDot={{ r: 4, fill: c.accent, stroke: c.bg }}
          isAnimationActive
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
