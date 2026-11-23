import { describe, expect, it } from "vitest";
import { DEFAULTS, nextState, parseState, serializeState } from "./urlState";

describe("url state", () => {
  it("round-trips a shared link", () => {
    const s = { view: "overview", region: "NY", offense: "robbery", agency: "NY0303000", compare: "TX" };
    expect(parseState(serializeState(s))).toEqual(s);
    expect(serializeState(DEFAULTS)).toBe("");
  });

  it("drops malformed values instead of trusting them", () => {
    expect(parseState("?region=New%20York&agency=../x&offense=<script>&view=ok")).toEqual({
      ...DEFAULTS,
      view: "ok",
    });
  });

  it("clears the agency when the region changes (BUG-3)", () => {
    const s = { ...DEFAULTS, region: "NY", agency: "NY0303000" };
    expect(nextState(s, { region: "TX" }).agency).toBeNull();
    expect(nextState(s, { offense: "rape" }).agency).toBe("NY0303000");
  });

  it("drops a comparison with the new region itself", () => {
    const s = { ...DEFAULTS, region: "NY", compare: "TX" };
    expect(nextState(s, { region: "TX" }).compare).toBeNull();
  });
});
