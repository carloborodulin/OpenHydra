import {
  Area,
  AreaChart,
  Bar,
  CartesianGrid,
  ComposedChart,
  LabelList,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useChartColors } from "../../lib/theme";
import { useIsMobile } from "../../lib/useMediaQuery";
import { DarkTooltip } from "./DarkTooltip";

// One row per year: crime volume, mean clearance ratio, and staffing per 1k.
export interface PerfYear {
  year: number;
  volume: number | null;
  clearance: number | null; // ratio 0..1
  staffing: number | null; // law-enforcement employees per 1,000 people
}

const compact = (v: number) => Intl.NumberFormat("en", { notation: "compact" }).format(v);

// Annual crime volume (bars, left) against mean clearance rate (line, right) — the
// report's "as volume surges, clearance falls" relationship.
export function VolumeClearanceChart({ data }: { data: PerfYear[] }) {
  const c = useChartColors();
  const mobile = useIsMobile();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const rows = data.map((d) => ({
    year: String(d.year),
    Volume: d.volume,
    "Clearance %": d.clearance == null ? null : +(d.clearance * 100).toFixed(1),
  }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ComposedChart data={rows} margin={{ top: 6, right: 8, bottom: 0, left: -6 }}>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="year" tick={tick} stroke={c.axis} />
        <YAxis yAxisId="vol" tick={tick} width={mobile ? 38 : 46} stroke={c.axis} tickFormatter={compact} />
        <YAxis
          yAxisId="clr"
          orientation="right"
          tick={tick}
          width={mobile ? 34 : 40}
          stroke={c.axis}
          domain={[0, "auto"]}
          tickFormatter={(v: number) => `${v}%`}
        />
        <Tooltip content={<DarkTooltip />} cursor={{ fill: c.grid, fillOpacity: 0.4 }} />
        <Legend wrapperStyle={{ fontFamily: c.font, fontSize: 10, color: c.muted }} />
        <Bar yAxisId="vol" dataKey="Volume" fill={c.accent} fillOpacity={0.35} maxBarSize={40} />
        <Line
          yAxisId="clr"
          type="monotone"
          dataKey="Clearance %"
          stroke={c.warn}
          strokeWidth={2}
          dot={false}
          connectNulls
          activeDot={{ r: 4, fill: c.warn, stroke: c.bg }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function ScatterTip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: { year: number; x: number | null; y: number | null } }>;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="panel mono px-3 py-2 text-[0.7rem]">
      <div className="mb-1 text-accent">{p.year}</div>
      <div className="text-ink">Staffing: {p.x == null ? "—" : `${p.x.toFixed(2)} /1k`}</div>
      <div className="text-ink">Clearance: {p.y == null ? "—" : `${p.y.toFixed(1)}%`}</div>
    </div>
  );
}

// Cumulative share of agencies reporting via NIBRS, by year — a data-quality /
// reporting-integrity tracker. The 2021 SRS→NIBRS transition shows as a jump.
export function NibrsAdoptionChart({ data }: { data: { year: number; pct: number }[] }) {
  const c = useChartColors();
  const mobile = useIsMobile();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const rows = data.map((d) => ({ year: String(d.year), "NIBRS %": +d.pct.toFixed(1) }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={rows} margin={{ top: 6, right: 14, bottom: 0, left: -10 }}>
        <defs>
          <linearGradient id="g-nibrs" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={c.good} stopOpacity={0.5} />
            <stop offset="100%" stopColor={c.good} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={c.grid} vertical={false} />
        <XAxis dataKey="year" tick={tick} stroke={c.axis} />
        <YAxis tick={tick} width={mobile ? 34 : 40} stroke={c.axis} domain={[0, 100]} tickFormatter={(v: number) => `${v}%`} />
        <Tooltip content={<DarkTooltip unit="%" />} cursor={{ stroke: c.axis }} />
        <Area
          type="monotone"
          dataKey="NIBRS %"
          stroke={c.good}
          strokeWidth={2}
          fill="url(#g-nibrs)"
          dot={false}
          activeDot={{ r: 4, fill: c.good, stroke: c.bg }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

// Each point is a year: staffing per 1k (x) vs mean clearance rate (y). Reveals
// whether more officers per capita tracks higher clearance.
export function StaffingClearanceScatter({ data }: { data: PerfYear[] }) {
  const c = useChartColors();
  const mobile = useIsMobile();
  const tick = { fill: c.muted, fontSize: 10, fontFamily: c.font };
  const points = data
    .filter((d) => d.staffing != null && d.clearance != null)
    .map((d) => ({ year: d.year, x: d.staffing, y: +((d.clearance as number) * 100).toFixed(1) }));
  return (
    <ResponsiveContainer width="100%" height="100%">
      <ScatterChart margin={{ top: 10, right: 16, bottom: 4, left: -6 }}>
        <CartesianGrid stroke={c.grid} />
        <XAxis
          type="number"
          dataKey="x"
          name="Staffing /1k"
          tick={tick}
          stroke={c.axis}
          domain={["auto", "auto"]}
          tickFormatter={(v: number) => v.toFixed(1)}
        />
        <YAxis
          type="number"
          dataKey="y"
          name="Clearance %"
          tick={tick}
          width={mobile ? 34 : 40}
          stroke={c.axis}
          tickFormatter={(v: number) => `${v}%`}
        />
        <Tooltip content={<ScatterTip />} cursor={{ stroke: c.axis, strokeDasharray: "3 3" }} />
        <Scatter data={points} fill={c.accent}>
          <LabelList
            dataKey="year"
            position="top"
            style={{ fill: c.muted, fontSize: 9, fontFamily: c.font }}
          />
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
