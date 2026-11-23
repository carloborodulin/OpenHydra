import { describe, expect, it } from "vitest";
import { ApiError } from "./api";
import { describeError } from "./errors";

describe("describeError", () => {
  it("separates an outage from missing data", () => {
    expect(describeError(new ApiError(502, "upstream_error", null, "x")).text).toMatch(/FBI data service/);
    expect(describeError(new ApiError(404, null, null, "x"))).toMatchObject({
      text: "There is no data for this selection.",
      retryable: false,
    });
  });

  it("keeps the Retry-After of a rate limit", () => {
    const v = describeError(new ApiError(429, "rate_limited", 12, "x"));
    expect(v.retryAfter).toBe(12);
    expect(v.retryable).toBe(true);
  });

  it("explains an unconfigured server and a network failure", () => {
    expect(describeError(new ApiError(503, "live_data_unconfigured", null, "x")).retryable).toBe(false);
    expect(describeError(new ApiError(0, "network", null, "x")).text).toMatch(/network/);
  });
});
