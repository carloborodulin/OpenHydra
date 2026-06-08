type Accent = "accent" | "warn" | "alert" | "good" | "violet";

interface Props {
  label: string;
  value: string;
  sub?: string;
  accent?: Accent;
}

export function StatTile({ label, value, sub, accent = "accent" }: Props) {
  return (
    <div className="panel brackets enter flex flex-col justify-between gap-1 px-4 py-3">
      <span className="panel-title">{label}</span>
      <span
        className="display glow text-3xl leading-none font-bold tabular-nums"
        style={{ color: `var(--color-${accent})` }}
      >
        {value}
      </span>
      <span className="mono text-[0.62rem] tracking-wide text-muted uppercase">{sub ?? " "}</span>
    </div>
  );
}
