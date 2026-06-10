import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { OffenseMonthly } from "../../lib/api";
import { monthLabel } from "../../lib/format";
import { useChartColors } from "../../lib/theme";
import { DarkTooltip } from "./DarkTooltip";

export function ClearanceChart({ data }: { data: OffenseMonthly[] }) {
  const c = useChartColors();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const rows = data
    .filter((d) => d.clearance_ratio != null)
    .map((d) => ({ period: monthLabel(d.period), Cleared: d.clearance_ratio }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={rows} margin={{ top: 6, right: 14, bottom: 0, left: -10 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="period" tick={tick} minTickGap={48} stroke={c.axis} />
        <YAxis
          tick={tick}
          width={42}
          stroke={c.axis}
          tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
        />
        <Tooltip content={<DarkTooltip percent />} cursor={{ stroke: c.axis }} />
        <Line
          type="monotone"
          dataKey="Cleared"
          stroke={c.warn}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: c.warn, stroke: c.bg }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
