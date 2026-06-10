import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

export const useMeta = () => useQuery({ queryKey: ["meta"], queryFn: api.meta });

export const useOffenseMonthly = (offense: string, level = "national", area = "US") =>
  useQuery({
    queryKey: ["offense-monthly", offense, level, area],
    queryFn: () => api.offensesMonthly(offense, level, area),
    enabled: Boolean(offense),
  });

export const useArrests = (
  category: string,
  offense?: string,
  level = "national",
  area = "US",
) =>
  useQuery({
    queryKey: ["arrests", category, offense, level, area],
    queryFn: () => api.arrests(category, offense, level, area),
  });

// Hate crime breakdowns. `category` undefined => all dimensions at once.
export const useHateCrime = (category: string | undefined, level = "national", area = "US") =>
  useQuery({
    queryKey: ["hate-crime", category, level, area],
    queryFn: () => api.hateCrime(category, level, area),
  });

export const useAgencyHateCrime = (ori: string | undefined, category?: string) =>
  useQuery({
    queryKey: ["agency-hate-crime", ori, category],
    queryFn: () => api.agencyHateCrime(ori as string, category),
    enabled: Boolean(ori),
  });

// Expanded homicide (SHR). `category` undefined => all section_dimensions.
export const useShr = (category: string | undefined, level = "national", area = "US") =>
  useQuery({
    queryKey: ["shr", category, level, area],
    queryFn: () => api.shr(category, level, area),
  });

export const useAgencyShr = (ori: string | undefined, category?: string) =>
  useQuery({
    queryKey: ["agency-shr", ori, category],
    queryFn: () => api.agencyShr(ori as string, category),
    enabled: Boolean(ori),
  });

// Expanded property. `offense` is NB/NL/NMVT/NROB; `category` undefined => all dims.
export const useProperty = (
  offense: string,
  category: string | undefined,
  level = "national",
  area = "US",
) =>
  useQuery({
    queryKey: ["property", offense, category, level, area],
    queryFn: () => api.property(offense, category, level, area),
    enabled: Boolean(offense),
  });

export const useAgencyProperty = (ori: string | undefined, offense: string, category?: string) =>
  useQuery({
    queryKey: ["agency-property", ori, offense, category],
    queryFn: () => api.agencyProperty(ori as string, offense, category),
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
    queryFn: () => api.nibrs(offense, category, level, area),
    enabled: Boolean(offense),
  });

export const useAgencyNibrs = (ori: string | undefined, offense: string, category?: string) =>
  useQuery({
    queryKey: ["agency-nibrs", ori, offense, category],
    queryFn: () => api.agencyNibrs(ori as string, offense, category),
    enabled: Boolean(ori),
  });

// LESDC — national only, by year + chart type.
export const useLesdc = (chartType: string, year: number, section?: string) =>
  useQuery({
    queryKey: ["lesdc", chartType, year, section],
    queryFn: () => api.lesdc(chartType, year, section),
    enabled: Boolean(chartType),
  });

// `state` undefined => all agencies (national view).
export const useAgencies = (state?: string) =>
  useQuery({ queryKey: ["agencies", state ?? "all"], queryFn: () => api.agencies(state) });

export const usePoliceEmployment = (level = "national", area = "US") =>
  useQuery({
    queryKey: ["police-employment", level, area],
    queryFn: () => api.policeEmployment(level, area),
  });

// Agency drill-down hooks — disabled until an agency (ori) is selected.
export const useAgencyOffenseMonthly = (ori: string | undefined, offense: string) =>
  useQuery({
    queryKey: ["agency-offense-monthly", ori, offense],
    queryFn: () => api.agencyOffenses(ori as string, offense),
    enabled: Boolean(ori && offense),
  });

export const useAgencyArrests = (
  ori: string | undefined,
  category: string,
  offense?: string,
) =>
  useQuery({
    queryKey: ["agency-arrests", ori, category, offense],
    queryFn: () => api.agencyArrests(ori as string, category, offense),
    enabled: Boolean(ori),
  });

export const useAgencyPoliceEmployment = (ori: string | undefined) =>
  useQuery({
    queryKey: ["agency-pe", ori],
    queryFn: () => api.agencyPoliceEmployment(ori as string),
    enabled: Boolean(ori),
  });
