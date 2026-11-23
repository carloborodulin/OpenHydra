import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "./api";
import { useAgencyOffenseMonthly } from "./queries";

function harness(liveAgency: boolean) {
  const calls: string[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      calls.push(url);
      const body = url.includes("/meta")
        ? { snapshot: null, capabilities: { live_agency: liveAgency } }
        : [];
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { calls, wrapper };
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("live agency queries", () => {
  it("make no request when the server has no FBI key", async () => {
    const { calls, wrapper } = harness(false);
    const { result } = renderHook(() => useAgencyOffenseMonthly("NY0303000", "homicide"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect((result.current.error as ApiError).code).toBe("live_data_unconfigured");
    expect(calls.filter((u) => u.includes("/agency/"))).toEqual([]);
  });

  it("call the live route when the server has a key", async () => {
    const { calls, wrapper } = harness(true);
    const { result } = renderHook(() => useAgencyOffenseMonthly("NY0303000", "homicide"), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(calls.some((u) => u.includes("/api/v1/agency/NY0303000/offenses"))).toBe(true);
  });
});
