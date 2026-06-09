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

// `state` undefined => all agencies (national view).
export const useAgencies = (state?: string) =>
  useQuery({ queryKey: ["agencies", state ?? "all"], queryFn: () => api.agencies(state) });

export const usePoliceEmployment = (level = "national", area = "US") =>
  useQuery({
    queryKey: ["police-employment", level, area],
    queryFn: () => api.policeEmployment(level, area),
  });
