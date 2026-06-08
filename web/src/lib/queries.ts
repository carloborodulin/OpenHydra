import { useQuery } from "@tanstack/react-query";
import { api } from "./api";

export const useMeta = () => useQuery({ queryKey: ["meta"], queryFn: api.meta });

export const useOffenseMonthly = (offense: string) =>
  useQuery({
    queryKey: ["offense-monthly", offense],
    queryFn: () => api.offensesMonthly(offense),
    enabled: Boolean(offense),
  });

export const useArrests = (category: string) =>
  useQuery({ queryKey: ["arrests", category], queryFn: () => api.arrests(category) });

export const useAgencies = (state: string) =>
  useQuery({ queryKey: ["agencies", state], queryFn: () => api.agencies(state) });
