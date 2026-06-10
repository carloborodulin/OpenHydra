import { useShr } from "../lib/queries";
import { BreakdownView, type Dimension } from "./BreakdownView";

// Supplementary Homicide Report dimensions (the API also returns victim/offender
// sex & ethnicity, which can be added later).
const DIMENSIONS: Dimension[] = [
  { key: "offense_weapons", label: "Weapon" },
  { key: "offense_circumstance", label: "Circumstance" },
  { key: "offense_relationship", label: "Victim–Offender Relationship" },
  { key: "victim_race", label: "Victim Race" },
  { key: "victim_age", label: "Victim Age" },
  { key: "offender_race", label: "Offender Race" },
];

export function HomicideView({ region }: { region: string }) {
  const level = region === "US" ? "national" : "state";
  const query = useShr(undefined, level, region);
  return <BreakdownView region={region} query={query} dimensions={DIMENSIONS} />;
}
