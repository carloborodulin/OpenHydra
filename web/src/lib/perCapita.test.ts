import { describe, expect, it } from "vitest";
import { perCapitaBasis } from "./perCapita";

const pop = [
  { year: 2022, population: 100 },
  { year: 2023, population: 200 },
  { year: 2024, population: 400 },
];

describe("perCapitaBasis", () => {
  it("uses the population of the same year for annual data", () => {
    const b = perCapitaBasis(pop, 2023, "2015–2024");
    expect(b.population).toBe(200);
    expect(b.unit).toBe("$ per resident, 2023");
  });

  it("labels a window total divided by the last population explicitly", () => {
    const b = perCapitaBasis(pop, null, "2015–2024");
    expect(b.population).toBe(400);
    expect(b.unit).toBe("$ per resident: 2015–2024 total ÷ 2024 population");
  });

  it("gives no denominator when the area has no population", () => {
    expect(perCapitaBasis([], 2023, "x").population).toBeNull();
    expect(perCapitaBasis(pop, 2019, "x").population).toBeNull();
  });
});
