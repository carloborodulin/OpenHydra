import { useState } from "react";
import { Select } from "../components/Select";
import { useNibrsEstimation } from "../lib/queries";
import { BreakdownView, type Dimension } from "./BreakdownView";

// Curated NIBRS-estimation offense codes (mirrors NIBRS_ESTIMATION_OFFENSES).
const OFFENSES: { code: string; label: string }[] = [
  { code: "133", label: "Violent Crime" },
  { code: "116", label: "Property Crime" },
  { code: "55", label: "Aggravated Assault" },
  { code: "124", label: "Simple Assault" },
  { code: "106", label: "Murder & Non-negligent Manslaughter" },
  { code: "118", label: "Rape" },
  { code: "121", label: "Robbery" },
  { code: "61", label: "Burglary / B&E" },
  { code: "102", label: "Larceny / Theft" },
  { code: "105", label: "Motor Vehicle Theft" },
  { code: "71", label: "Drug / Narcotic Offenses" },
  { code: "68", label: "Destruction / Vandalism" },
];

const GEOS: { level: string; area: string; label: string }[] = [
  { level: "national", area: "US", label: "National" },
  { level: "region", area: "Midwest", label: "Midwest" },
  { level: "region", area: "Northeast", label: "Northeast" },
  { level: "region", area: "South", label: "South" },
  { level: "region", area: "West", label: "West" },
];

const DIMENSIONS: Dimension[] = [
  { key: "Offense_Location type", label: "Location" },
  { key: "Offense_Type of Weapon Involved", label: "Weapon" },
  { key: "Victim_Victim race", label: "Victim Race" },
  { key: "Victim_Victim age", label: "Victim Age" },
  { key: "Arrest_Arrestee race", label: "Arrestee Race" },
  { key: "Incident_Clearance Status", label: "Clearance Status" },
];

export function NibrsEstimationView() {
  const [offense, setOffense] = useState("133");
  const [geoIdx, setGeoIdx] = useState(0);
  const geo = GEOS[geoIdx];
  const query = useNibrsEstimation(geo.level, geo.area, offense);

  return (
    <>
      <div className="mx-3 mt-3 flex flex-wrap items-center gap-3">
        <span className="panel-title shrink-0">Estimated · Offense</span>
        <Select
          value={offense}
          onChange={setOffense}
          options={OFFENSES.map((o) => ({ value: o.code, label: o.label }))}
          title="Estimation offense"
          className="w-60"
        />
        <span className="h-4 w-px bg-line" />
        <div className="flex flex-wrap gap-1.5">
          {GEOS.map((g, i) => {
            const on = i === geoIdx;
            return (
              <button
                key={g.label}
                type="button"
                onClick={() => setGeoIdx(i)}
                className={`mono cursor-pointer border px-2.5 py-1 text-[0.62rem] tracking-wider uppercase transition ${
                  on
                    ? "glow border-accent bg-accent/10 text-accent"
                    : "border-line text-muted hover:border-line-strong hover:text-ink"
                }`}
              >
                {g.label}
              </button>
            );
          })}
        </div>
      </div>
      <BreakdownView region={geo.label} query={query} dimensions={DIMENSIONS} />
    </>
  );
}
