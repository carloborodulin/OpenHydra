import { useHateCrime } from "../lib/queries";
import { BreakdownView, type Dimension } from "./BreakdownView";

// Curated dimensions to surface (the API also returns judicial_district and
// offender_ethnicity, which can be added later).
const DIMENSIONS: Dimension[] = [
  { key: "bias_category", label: "Bias Category" },
  { key: "bias", label: "Bias Motivation" },
  { key: "offender_race", label: "Offender Race" },
  { key: "victim_type", label: "Victim Type" },
  { key: "location_type", label: "Location Type" },
  { key: "offense_type", label: "Offense Type" },
];

export function HateCrimeView({ region }: { region: string }) {
  const level = region === "US" ? "national" : "state";
  const query = useHateCrime(undefined, level, region);
  return <BreakdownView region={region} query={query} dimensions={DIMENSIONS} />;
}
