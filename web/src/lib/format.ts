export const titleCase = (slug: string): string =>
  slug
    .split("-")
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(" ");

const compact = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

export const fmtNum = (v: number | null | undefined): string => (v == null ? "—" : compact.format(v));
export const fmtPct = (v: number | null | undefined, d = 1): string =>
  v == null ? "—" : `${(v * 100).toFixed(d)}%`;
export const fmtRate = (v: number | null | undefined, d = 2): string =>
  v == null ? "—" : v.toFixed(d);
export const monthLabel = (iso: string): string => iso.slice(0, 7); // YYYY-MM

export const lastNonNull = <K extends string>(
  rows: Array<Record<K, number | null> & { period: string }>,
  key: K,
): { value: number; period: string } | null => {
  for (let i = rows.length - 1; i >= 0; i--) {
    const v = rows[i][key];
    if (v != null) return { value: v, period: rows[i].period };
  }
  return null;
};
