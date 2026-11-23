import type { ReactNode } from "react";

type Accent = "accent" | "warn" | "alert" | "good" | "violet";

interface Props {
  label: string;
  value: string;
  sub?: string;
  accent?: Accent;
  // Optional badge shown to the right of the value (e.g. a <DeltaIndicator/>).
  delta?: ReactNode;
  // The id of the definition in the Methodology view (see MethodologyView).
  help?: string;
}

export function StatTile({ label, value, sub, accent = "accent", delta, help }: Props) {
  return (
    <div className="panel brackets enter flex flex-col justify-between gap-1 px-4 py-3">
      <span className="flex items-center justify-between gap-2">
        <span className="panel-title block truncate">{label}</span>
        {help && (
          <a
            href={`?view=methodology#${help}`}
            className="mono shrink-0 text-[0.6rem] text-muted underline hover:text-accent"
            // The name starts with the visible text (WCAG 2.5.3, label in name).
            aria-label={`def: definition of ${label}`}
          >
            def
          </a>
        )}
      </span>
      <div className="flex min-w-0 items-end justify-between gap-2">
        <span
          className="display glow text-[clamp(1.4rem,4.2vw,1.875rem)] leading-none font-bold tabular-nums"
          style={{ color: `var(--color-${accent})` }}
        >
          {value}
        </span>
        {delta}
      </div>
      <span className="mono block truncate text-[0.62rem] tracking-wide text-muted uppercase">
        {sub ?? " "}
      </span>
    </div>
  );
}
