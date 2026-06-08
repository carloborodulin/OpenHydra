interface TipItem {
  name?: string | number;
  value?: number | string;
  color?: string;
}

interface Props {
  active?: boolean;
  payload?: TipItem[];
  label?: string | number;
  unit?: string;
  percent?: boolean;
}

export function DarkTooltip({ active, payload, label, unit = "", percent = false }: Props) {
  if (!active || !payload?.length) return null;
  const fmt = (v: number | string | undefined) => {
    if (typeof v !== "number") return v ?? "—";
    return percent ? `${(v * 100).toFixed(1)}%` : v.toLocaleString();
  };
  return (
    <div className="panel mono px-3 py-2 text-[0.7rem]">
      <div className="mb-1 text-accent">{label}</div>
      {payload.map((p, i) => (
        <div key={i} className="text-ink">
          {p.name}: <span style={{ color: p.color ?? "var(--color-good)" }}>{fmt(p.value)}{unit}</span>
        </div>
      ))}
    </div>
  );
}
