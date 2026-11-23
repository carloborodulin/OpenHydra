import type { RefObject } from "react";
import { captionLines, chartPng, download, fileName, toCsv } from "../../lib/exporting";
import { useRelease } from "../../lib/release";

/** "CSV" and "PNG" buttons for one chart. */
export function ExportButtons({
  title,
  rows,
  unit,
  grain,
  chartRef,
}: {
  title: string;
  rows: Record<string, unknown>[];
  unit?: string;
  grain?: string;
  chartRef: RefObject<HTMLElement | null>;
}) {
  const snapshot = useRelease();
  const btn =
    "cursor-pointer border border-line px-1.5 py-0.5 text-[0.58rem] tracking-wider uppercase hover:border-line-strong hover:text-ink";
  return (
    <span className="ml-auto flex gap-1">
      <button
        type="button"
        className={btn}
        aria-label={`Download ${title} as CSV`}
        onClick={() =>
          download(
            fileName(title, "csv"),
            new Blob([toCsv(rows, { title, unit, grain, snapshot })], { type: "text/csv" }),
          )
        }
      >
        CSV
      </button>
      <button
        type="button"
        className={btn}
        aria-label={`Download ${title} as PNG`}
        onClick={async () => {
          if (!chartRef.current) return;
          const png = await chartPng(chartRef.current, captionLines(title, snapshot));
          if (png) download(fileName(title, "png"), png);
        }}
      >
        PNG
      </button>
    </span>
  );
}
