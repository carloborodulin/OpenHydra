import { useQuery } from "@tanstack/react-query";
import { api, pointsToAgencies, withSignal } from "./api";

export const useMeta = () =>
  useQuery({ queryKey: ["meta"], queryFn: ({ signal }) => withSignal(signal, () => api.meta()) });

export const useOffenseMonthly = (
  offense: string,
  level = "national",
  area = "US",
  enabled = true,
) =>
  useQuery({
    queryKey: ["offense-monthly", offense, level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.offensesMonthly(offense, level, area)),
    enabled: enabled && Boolean(offense) && Boolean(area),
  });

// Area-vs-national benchmark for an offense. Only meaningful for a state/agency area;
// disabled (and pointless) at the national level. `enabled` guards both.
export const useOffenseBenchmark = (offense: string, level: string, area: string, enabled = true) =>
  useQuery({
    queryKey: ["offense-benchmark", offense, level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.offensesBenchmark(offense, level, area)),
    enabled: enabled && Boolean(offense),
  });

export const useArrestsAvailable = (level = "national", area = "US", enabled = true) =>
  useQuery({
    queryKey: ["arrests-available", level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.arrestsAvailable(level, area)),
    enabled,
  });

export const useArrests = (category: string, offense?: string, level = "national", area = "US") =>
  useQuery({
    queryKey: ["arrests", category, offense, level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.arrests(category, offense, level, area)),
  });

// Hate crime breakdowns. `category` undefined => all dimensions at once.
export const useHateCrime = (category: string | undefined, level = "national", area = "US") =>
  useQuery({
    queryKey: ["hate-crime", category, level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.hateCrime(category, level, area)),
  });

export const useAgencyHateCrime = (ori: string | undefined, category?: string) =>
  useQuery({
    queryKey: ["agency-hate-crime", ori, category],
    queryFn: ({ signal }) => withSignal(signal, () => api.agencyHateCrime(ori as string, category)),
    enabled: Boolean(ori),
  });

// Expanded homicide (SHR). `category` undefined => all section_dimensions.
export const useShr = (category: string | undefined, level = "national", area = "US") =>
  useQuery({
    queryKey: ["shr", category, level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.shr(category, level, area)),
  });

export const useAgencyShr = (ori: string | undefined, category?: string) =>
  useQuery({
    queryKey: ["agency-shr", ori, category],
    queryFn: ({ signal }) => withSignal(signal, () => api.agencyShr(ori as string, category)),
    enabled: Boolean(ori),
  });

// Expanded property. `offense` is NB/NL/NMVT/NROB; `category` undefined => all dims.
export const useProperty = (
  offense: string,
  category: string | undefined,
  level = "national",
  area = "US",
  year?: number,
) =>
  useQuery({
    queryKey: ["property", offense, category, level, area, year ?? "latest"],
    queryFn: ({ signal }) =>
      withSignal(signal, () => api.property(offense, category, level, area, year)),
    enabled: Boolean(offense),
  });

export const usePropertyYears = (offense: string, level = "national", area = "US") =>
  useQuery({
    queryKey: ["property-years", offense, level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.propertyYears(offense, level, area)),
  });

export const useAgencyProperty = (ori: string | undefined, offense: string, category?: string) =>
  useQuery({
    queryKey: ["agency-property", ori, offense, category],
    queryFn: ({ signal }) =>
      withSignal(signal, () => api.agencyProperty(ori as string, offense, category)),
    enabled: Boolean(ori),
  });

// NIBRS incidents. `offense` is a NIBRS code; `category` undefined => all dims.
export const useNibrs = (
  offense: string,
  category: string | undefined,
  level = "national",
  area = "US",
) =>
  useQuery({
    queryKey: ["nibrs", offense, category, level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.nibrs(offense, category, level, area)),
    enabled: Boolean(offense),
  });

export const useAgencyNibrs = (ori: string | undefined, offense: string, category?: string) =>
  useQuery({
    queryKey: ["agency-nibrs", ori, offense, category],
    queryFn: ({ signal }) =>
      withSignal(signal, () => api.agencyNibrs(ori as string, offense, category)),
    enabled: Boolean(ori),
  });

// LESDC — national only, by year + chart type.
export const useLesdc = (chartType: string, year: number, section?: string) =>
  useQuery({
    queryKey: ["lesdc", chartType, year, section],
    queryFn: ({ signal }) => withSignal(signal, () => api.lesdc(chartType, year, section)),
    enabled: Boolean(chartType),
  });

// Use of Force — national only.
export const useUofParticipation = () =>
  useQuery({ queryKey: ["uof-participation"], queryFn: api.uofParticipation });

export const useUofQuestions = (year: number, category?: string) =>
  useQuery({
    queryKey: ["uof-questions", year, category],
    queryFn: ({ signal }) => withSignal(signal, () => api.uofQuestions(year, category)),
  });

// NIBRS estimations — national / region, numeric offense code.
export const useNibrsEstimation = (
  level: string,
  area: string,
  offense: string,
  category?: string,
) =>
  useQuery({
    queryKey: ["nibrs-estimation", level, area, offense, category],
    queryFn: ({ signal }) =>
      withSignal(signal, () => api.nibrsEstimation(level, area, offense, category)),
    enabled: Boolean(offense),
  });

// `state` undefined => all agencies (national view).
// The agency list for the map, the search and the counts. It uses the compact,
// release-versioned points route, so the browser caches it until the next release.
export const useAgencies = (state?: string) => {
  const release = useMeta().data?.snapshot?.release_id ?? "";
  return useQuery({
    queryKey: ["agencies", state ?? "all", release],
    queryFn: ({ signal }) =>
      withSignal(signal, () => api.agencyPoints(release, state)).then(pointsToAgencies),
    enabled: Boolean(release),
    staleTime: Infinity,
  });
};

export const usePoliceEmployment = (level = "national", area = "US") =>
  useQuery({
    queryKey: ["police-employment", level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.policeEmployment(level, area)),
  });

export const usePopulation = (level = "national", area = "US") =>
  useQuery({
    queryKey: ["population", level, area],
    queryFn: ({ signal }) => withSignal(signal, () => api.population(level, area)),
  });

// Agency drill-down hooks — disabled until an agency (ori) is selected.
export const useAgencyOffenseMonthly = (ori: string | undefined, offense: string) =>
  useQuery({
    queryKey: ["agency-offense-monthly", ori, offense],
    queryFn: ({ signal }) => withSignal(signal, () => api.agencyOffenses(ori as string, offense)),
    enabled: Boolean(ori && offense),
  });

export const useAgencyArrests = (ori: string | undefined, category: string, offense?: string) =>
  useQuery({
    queryKey: ["agency-arrests", ori, category, offense],
    queryFn: ({ signal }) =>
      withSignal(signal, () => api.agencyArrests(ori as string, category, offense)),
    enabled: Boolean(ori),
  });

export const useAgencyPoliceEmployment = (ori: string | undefined) =>
  useQuery({
    queryKey: ["agency-pe", ori],
    queryFn: ({ signal }) => withSignal(signal, () => api.agencyPoliceEmployment(ori as string)),
    enabled: Boolean(ori),
  });
