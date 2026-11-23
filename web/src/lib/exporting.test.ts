import { describe, expect, it } from "vitest";
import { fileName, toCsv } from "./exporting";

describe("toCsv", () => {
  it("states the unit, the grain and the release, and quotes values", () => {
    const csv = toCsv(
      [
        { label: 'Knife, "large"', value: 12 },
        { label: "None", value: 0 },
      ],
      {
        title: "Weapons",
        unit: "Victims",
        grain: "weapon",
        snapshot: {
          release_id: "R1",
          window_from: "01-2015",
          window_to: "12-2024",
          extracted_at_max: "2026-11-23T00:00:00",
        } as never,
      },
    );
    const lines = csv.trim().split("\n");
    expect(lines[0]).toBe("# Weapons");
    expect(lines).toContain("# Unit: Victims");
    expect(lines).toContain("# One row per: weapon");
    expect(lines.find((l) => l.includes("Release R1"))).toMatch(
      /01-2015–12-2024, extracted 2026-11-23/,
    );
    expect(lines.slice(-3)).toEqual(["label,value", '"Knife, ""large""",12', "None,0"]);
  });

  it("makes a safe file name", () => {
    expect(fileName("Offense Rate · Homicide / NY", "csv")).toBe("offense-rate-homicide-ny.csv");
  });
});
