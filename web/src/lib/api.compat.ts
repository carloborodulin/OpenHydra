// Compile-time check that the hand-written API types (api.ts) still match the
// API. api.gen.ts comes from the FastAPI OpenAPI document (CI regenerates it
// and fails on drift). When the API removes or renames a field that the
// dashboard reads, `tsc -b` fails here.
import type {
  AgencyFeature,
  AgencyPoints,
  ArrestAvailability,
  ArrestBreakdownRow,
  ArrestOffense,
  BenchmarkRow,
  EstimateRow,
  Meta,
  OffenseMonthly,
  PoliceEmploymentRow,
  PopulationRow,
  PropertyRow,
  PropertyYears,
  Snapshot,
  UofParticipationRow,
} from "./api";
import type { components } from "./api.gen";

type Schemas = components["schemas"];
/** Never unless every key of Mine is also a key of the API schema Api. */
type MissingKeys<Mine, Api> = Exclude<keyof Mine, keyof Api>;
type Check<T extends never> = T;

export type ApiCompat = [
  Check<MissingKeys<Meta, Schemas["Meta"]>>,
  Check<MissingKeys<Snapshot, Schemas["Snapshot"]>>,
  Check<MissingKeys<ArrestOffense, Schemas["ArrestOffense"]>>,
  Check<MissingKeys<OffenseMonthly, Schemas["OffenseMonthly"]>>,
  Check<MissingKeys<BenchmarkRow, Schemas["BenchmarkRow"]>>,
  Check<MissingKeys<AgencyFeature, Schemas["AgencyFeature"]>>,
  Check<MissingKeys<AgencyPoints, Schemas["AgencyPoints"]>>,
  Check<MissingKeys<ArrestBreakdownRow, Schemas["ArrestBreakdownRow"]>>,
  Check<MissingKeys<ArrestAvailability, Schemas["ArrestAvailability"]>>,
  Check<MissingKeys<PoliceEmploymentRow, Schemas["PoliceEmploymentRow"]>>,
  Check<MissingKeys<PopulationRow, Schemas["PopulationRow"]>>,
  Check<MissingKeys<PropertyRow, Schemas["PropertyRow"]>>,
  Check<MissingKeys<PropertyYears, Schemas["PropertyYears"]>>,
  Check<MissingKeys<EstimateRow, Schemas["EstimateRow"]>>,
  Check<MissingKeys<UofParticipationRow, Schemas["UofParticipationRow"]>>,
];
