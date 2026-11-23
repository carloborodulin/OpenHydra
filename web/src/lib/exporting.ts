import type { Snapshot } from "./api";

const cell = (v: unknown): string => {
  if (v == null) return "";
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
};

/**
 * A CSV of the rows a chart draws. The header lines (starting with "#") give
 * the chart, its unit, the grain of a row and the data release, so a saved
 * file says what it holds.
 */
export function toCsv(
  rows: Record<string, unknown>[],
  meta: { title: string; unit?: string; grain?: string; snapshot: Snapshot | null },
): string {
  const columns = rows.length ? Object.keys(rows[0]) : [];
  const s = meta.snapshot;
  const header = [
    `# ${meta.title}`,
    meta.unit ? `# Unit: ${meta.unit}` : null,
    `# One row per: ${meta.grain ?? columns[0] ?? "row"}`,
    `# Source: FBI Crime Data Explorer API. Release ${s?.release_id ?? "unknown"}` +
      (s
        ? `, data ${s.window_from}–${s.window_to}, extracted ${s.extracted_at_max?.slice(0, 10)}`
        : ""),
    "# Methodology: see the Methodology view of OpenHydra",
  ].filter(Boolean);
  const body = [
    columns.map(cell).join(","),
    ...rows.map((r) => columns.map((c) => cell(r[c])).join(",")),
  ];
  return [...header, ...body].join("\n") + "\n";
}

export function fileName(title: string, ext: string): string {
  return `${
    title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "") || "chart"
  }.${ext}`;
}

export function download(name: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * A PNG of the chart SVG in `container`, with a caption under it (the title,
 * the filters and the release), at twice the screen size.
 */
export async function chartPng(container: HTMLElement, caption: string[]): Promise<Blob | null> {
  const svg = container.querySelector("svg.recharts-surface");
  if (!svg) return null;
  const { width, height } = svg.getBoundingClientRect();
  const clone = svg.cloneNode(true) as SVGSVGElement;
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", String(width));
  clone.setAttribute("height", String(height));
  const style = getComputedStyle(document.body);
  const xml = new XMLSerializer().serializeToString(clone);
  const img = new Image();
  img.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(xml)}`;
  await img.decode();
  const scale = 2;
  const lineHeight = 16;
  const pad = 12;
  const canvas = document.createElement("canvas");
  canvas.width = Math.ceil(width * scale);
  canvas.height = Math.ceil((height + pad * 2 + caption.length * lineHeight) * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.scale(scale, scale);
  ctx.fillStyle = style.getPropertyValue("--color-bg2").trim() || "#ffffff";
  ctx.fillRect(0, 0, width, canvas.height / scale);
  ctx.drawImage(img, 0, 0, width, height);
  ctx.fillStyle = style.getPropertyValue("--color-ink").trim() || "#202124";
  ctx.font = "11px Inter, system-ui, sans-serif";
  caption.forEach((line, i) => ctx.fillText(line, pad, height + pad + (i + 1) * lineHeight - 4));
  return new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
}

export function captionLines(title: string, snapshot: Snapshot | null): string[] {
  const filters = new URLSearchParams(window.location.search);
  const scope = ["region", "offense", "agency", "compare"]
    .map((k) => (filters.get(k) ? `${k} ${filters.get(k)}` : null))
    .filter(Boolean)
    .join(" · ");
  return [
    title + (scope ? ` (${scope})` : ""),
    `FBI Crime Data Explorer API · release ${snapshot?.release_id ?? "unknown"} · ${window.location.origin}/?view=methodology`,
  ];
}
