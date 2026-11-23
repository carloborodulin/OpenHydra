import { describe, expect, it } from "vitest";
import { participationFacts } from "./participation";

describe("participationFacts", () => {
  it("keeps the FBI percentage and the agency share apart", () => {
    const f = participationFacts({
      year: 2022,
      participating_agencies: 10353,
      total_agencies: 18514,
      participation_percent: 75,
    });
    expect(f.fbiPercent).toBe("75%");
    expect(f.agencyShare).toBe("55.9%");
    expect(f.agencyLine).toBe("10,353 of 18,514 agencies");
  });

  it("shows an unknown value as a dash, not 0%", () => {
    const f = participationFacts({
      year: 2019,
      participating_agencies: null,
      total_agencies: null,
      participation_percent: null,
    });
    expect(f.fbiPercent).toBe("—");
    expect(f.agencyShare).toBe("—");
  });
});
