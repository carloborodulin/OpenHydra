import { fmtSignedPct } from "../lib/format";

// Compact ±% badge for a year-over-year (or vs-baseline) change. For crime metrics
// a falling value is "good" (green); a rising value is "bad" (alert/red). Flip with
// goodDirection="up" for metrics where more is better (e.g. clearance).
export function DeltaIndicator({
  value,
  label = "YoY",
  goodDirection = "down",
}: {
  value: number | null | undefined;
  label?: string;
  goodDirection?: "up" | "down";
}) {
  if (value == null) return null;
  const up = value > 0;
  const isGood = goodDirection === "up" ? up : !up;
  const color = value === 0 ? "muted" : isGood ? "good" : "alert";
  const arrow = value === 0 ? "→" : up ? "▲" : "▼";
  return (
    <span
      className="mono inline-flex items-center gap-1 text-[0.62rem] font-semibold tracking-wide tabular-nums"
      style={{ color: `var(--color-${color})` }}
      title={`${label}: ${fmtSignedPct(value)}`}
    >
      <span aria-hidden>{arrow}</span>
      {fmtSignedPct(value)}
      <span className="text-muted">{label}</span>
    </span>
  );
}
