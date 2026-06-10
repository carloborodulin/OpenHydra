import { useState } from "react";
import { useNibrs } from "../lib/queries";
import { BreakdownView, type Dimension } from "./BreakdownView";

// Curated NIBRS offenses (mirrors cdeclient NIBRS_OFFENSES) for the selector.
const OFFENSES: { code: string; label: string }[] = [
  { code: "09A", label: "Homicide" },
  { code: "11A", label: "Rape" },
  { code: "120", label: "Robbery" },
  { code: "13A", label: "Agg. Assault" },
  { code: "13B", label: "Simple Assault" },
  { code: "200", label: "Arson" },
  { code: "220", label: "Burglary" },
  { code: "23F", label: "Theft from Vehicle" },
  { code: "240", label: "MV Theft" },
  { code: "250", label: "Forgery" },
  { code: "35A", label: "Drugs" },
  { code: "520", label: "Weapons" },
];

const DIMENSIONS: Dimension[] = [
  { key: "offense_weapons", label: "Weapon" },
  { key: "victim_relationship", label: "Victim–Offender Relationship" },
  { key: "victim_location", label: "Location" },
  { key: "victim_race", label: "Victim Race" },
  { key: "offender_race", label: "Offender Race" },
  { key: "offender_age", label: "Offender Age" },
];

export function NibrsView({ region }: { region: string }) {
  const [offense, setOffense] = useState("13A");
  const level = region === "US" ? "national" : "state";
  const query = useNibrs(offense, undefined, level, region);

  return (
    <>
      <div className="mx-3 mt-3 flex flex-wrap items-center gap-2">
        <span className="panel-title shrink-0">NIBRS Offense</span>
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
                    ? "glow border-accent bg-accent/10 text-accent"
                    : "border-line text-muted hover:border-line-strong hover:text-ink"
                }`}
              >
                {o.label}
              </button>
            );
          })}
        </div>
      </div>
      <BreakdownView region={region} query={query} dimensions={DIMENSIONS} />
    </>
  );
}
