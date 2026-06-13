import type { ReactNode } from "react";

type Accent = "accent" | "warn" | "alert" | "good" | "violet";

interface Props {
  label: string;
  value: string;
  sub?: string;
  accent?: Accent;
  // Optional badge shown to the right of the value (e.g. a <DeltaIndicator/>).
  delta?: ReactNode;
}

export function StatTile({ label, value, sub, accent = "accent", delta }: Props) {
  return (
    <div className="panel brackets enter flex flex-col justify-between gap-1 px-4 py-3">
      <span className="panel-title block truncate">{label}</span>
      <div className="flex min-w-0 items-end justify-between gap-2">
        <span
          className="display glow text-[clamp(1.4rem,4.2vw,1.875rem)] leading-none font-bold tabular-nums"
          style={{ color: `var(--color-${accent})` }}
        >
          {value}
        </span>
        {delta}
      </div>
      <span className="mono block truncate text-[0.62rem] tracking-wide text-muted uppercase">{sub ?? " "}</span>
    </div>
  );
}
