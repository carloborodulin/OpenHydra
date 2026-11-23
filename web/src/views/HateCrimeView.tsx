import { useHateCrime } from "../lib/queries";
import { BreakdownView, type Dimension } from "./BreakdownView";

// Curated dimensions to surface. The API also returns judicial_district.
// The FBI removed victim_type from the response in 2026-11.
const DIMENSIONS: Dimension[] = [
  { key: "bias_category", label: "Bias Category" },
  { key: "bias", label: "Bias Motivation" },
  { key: "offender_race", label: "Offender Race" },
  { key: "offender_ethnicity", label: "Offender Ethnicity" },
  { key: "location_type", label: "Location Type" },
  { key: "offense_type", label: "Offense Type" },
];

export function HateCrimeView({ region }: { region: string }) {
  const level = region === "US" ? "national" : "state";
  const query = useHateCrime(undefined, level, region);
  return <BreakdownView domain="hate-crime" region={region} query={query} dimensions={DIMENSIONS} />;
}
