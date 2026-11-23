import type { PopulationRow } from "./api";

/** The dollar dimensions that make sense per resident (counts and averages do not). */
export const VALUE_CATS = new Set(["stolen_value", "recovered_value"]);

export interface PerCapitaBasis {
  /** The population to divide by, or null when the area has none for that year. */
  population: number | null;
  /** The year of that population. */
  populationYear: number | null;
  /** The unit label for the chart, for example "$ per resident, 2023". */
  unit: string;
}

/**
 * The denominator for "dollars per resident".
 *
 * - Annual data (year set): the Census population of the same year.
 * - Window totals (year null, an older snapshot): the window total divided by
 *   the population of the last window year. The label says so.
 * - No population for the area (for example FS or VI): null, so the
 *   dashboard leaves the per-resident view empty instead of guessing.
 */
export function perCapitaBasis(
  population: PopulationRow[],
  year: number | null,
  windowLabel: string,
): PerCapitaBasis {
  if (year != null) {
    const row = population.find((p) => p.year === year);
    return {
      population: row?.population ?? null,
      populationYear: row ? year : null,
      unit: `$ per resident, ${year}`,
    };
  }
  const last = [...population].sort((a, b) => a.year - b.year).at(-1);
  return {
    population: last?.population ?? null,
    populationYear: last?.year ?? null,
    unit: last ? `$ per resident: ${windowLabel} total ÷ ${last.year} population` : "$ per resident",
  };
}
