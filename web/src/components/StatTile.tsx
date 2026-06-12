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
      <span className="panel-title">{label}</span>
      <div className="flex items-end justify-between gap-2">
        <span
          className="display glow text-3xl leading-none font-bold tabular-nums"
          style={{ color: `var(--color-${accent})` }}
        >
          {value}
        </span>
        {delta}
      </div>
      <span className="mono text-[0.62rem] tracking-wide text-muted uppercase">{sub ?? " "}</span>
    </div>
  );
}
