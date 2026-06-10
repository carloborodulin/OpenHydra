import { useState } from "react";
import { useProperty } from "../lib/queries";
import { BreakdownView } from "./BreakdownView";

const OFFENSES: { code: string; label: string }[] = [
  { code: "NB", label: "Burglary" },
  { code: "NL", label: "Larceny" },
  { code: "NMVT", label: "Motor Vehicle Theft" },
  { code: "NROB", label: "Robbery" },
];

export function PropertyView({ region }: { region: string }) {
  const [offense, setOffense] = useState("NB");
  const level = region === "US" ? "national" : "state";
  // All dimensions for the chosen offense; BreakdownView derives the panels
  // (stolen/recovered value, location counts & average value — varies by offense).
  const query = useProperty(offense, undefined, level, region);

  return (
    <>
      <div className="mx-3 mt-3 flex flex-wrap items-center gap-2">
        <span className="panel-title shrink-0">Property Offense</span>
        <div className="flex flex-wrap gap-1.5">
          {OFFENSES.map((o) => {
            const on = o.code === offense;
            return (
              <button
                key={o.code}
                type="button"
                onClick={() => setOffense(o.code)}
                className={`mono cursor-pointer border px-2.5 py-1 text-[0.62rem] tracking-wider uppercase transition ${
                  on
                    ? "glow border-accent bg-[rgba(34,211,238,0.1)] text-accent"
                    : "border-line text-muted hover:border-line-strong hover:text-ink"
                }`}
              >
                {o.label}
              </button>
            );
          })}
        </div>
      </div>
      <BreakdownView region={region} query={query} />
    </>
  );
}
