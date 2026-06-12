import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BenchmarkRow, OffenseMonthly } from "../../lib/api";
import { monthLabel } from "../../lib/format";
import { useChartColors } from "../../lib/theme";
import { DarkTooltip } from "./DarkTooltip";

export type TrendMode = "rate" | "index" | "relative";

// `rate` plots the raw monthly rate (with an optional dashed national overlay when
// `benchmark` is supplied for a state/agency); `index` plots the 2019-indexed
// (de-seasonalized) series; `relative` plots the area's rate as a % of national.
// `index`/`relative` draw a 100 baseline reference line.
export function TrendChart({
  data,
  mode = "rate",
  benchmark,
}: {
  data: OffenseMonthly[];
  mode?: TrendMode;
  benchmark?: BenchmarkRow[];
}) {
  const c = useChartColors();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const bench = new Map((benchmark ?? []).map((b) => [monthLabel(b.period), b]));

  const key = mode === "index" ? "Index" : mode === "relative" ? "vs US" : "Rate";
  const showNational = mode === "rate" && bench.size > 0;
  const baseline = mode === "index" || mode === "relative";

  const rows = data.map((d) => {
    const p = monthLabel(d.period);
    const b = bench.get(p);
    return {
      period: p,
      [key]:
        mode === "index"
          ? d.index_2019
          : mode === "relative"
            ? (b?.relative_index ?? null)
            : d.offenses_rate,
      ...(showNational ? { National: b?.national_rate ?? null } : {}),
    };
  });

  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={rows} margin={{ top: 6, right: 14, bottom: 0, left: -10 }}>
        <defs>
          <linearGradient id="g-rate" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={c.accent} stopOpacity={0.5} />
            <stop offset="100%" stopColor={c.accent} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="period" tick={tick} minTickGap={48} stroke={c.axis} />
        <YAxis tick={tick} width={42} stroke={c.axis} domain={baseline ? ["auto", "auto"] : undefined} />
        <Tooltip content={<DarkTooltip unit={mode === "rate" ? " /100k" : ""} />} cursor={{ stroke: c.axis }} />
        {showNational && (
          <Legend wrapperStyle={{ fontFamily: c.font, fontSize: 10, color: c.muted }} />
        )}
        {baseline && (
          <ReferenceLine
            y={100}
            stroke={c.axis}
            strokeDasharray="4 4"
            label={{
              value: mode === "index" ? "2019" : "US",
              fill: c.muted,
              fontSize: 9,
              position: "insideTopLeft",
            }}
          />
        )}
        <Area
          type="monotone"
          dataKey={key}
          stroke={c.accent}
          strokeWidth={2}
          fill="url(#g-rate)"
          dot={false}
          activeDot={{ r: 4, fill: c.accent, stroke: c.bg }}
          isAnimationActive
        />
        {showNational && (
          <Line
            type="monotone"
            dataKey="National"
            stroke={c.violet}
            strokeWidth={1.5}
            strokeDasharray="5 4"
            dot={false}
            connectNulls
            isAnimationActive={false}
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
