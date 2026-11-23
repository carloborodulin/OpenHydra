import { ApiError } from "./api";

export interface ErrorView {
  /** One short sentence for the panel. */
  text: string;
  /** Seconds to wait before a retry can help, if the API said so. */
  retryAfter: number | null;
  /** False when a retry cannot help (for example an unknown agency). */
  retryable: boolean;
}

/** Turn a query error into a message that says what failed and what still works. */
export function describeError(err: unknown): ErrorView {
  if (!(err instanceof ApiError)) {
    return {
      text: "Something failed while loading this panel.",
      retryAfter: null,
      retryable: true,
    };
  }
  const wait = err.retryAfter;
  switch (err.code) {
    case "network":
      return {
        text: "The server cannot be reached. Check the network connection.",
        retryAfter: null,
        retryable: true,
      };
    case "rate_limited":
      return {
        text: "Too many live agency requests from this browser.",
        retryAfter: wait,
        retryable: true,
      };
    case "live_budget_spent":
    case "upstream_rate_limited":
      return {
        text: "The hourly budget for live FBI data is spent. The snapshot views still work.",
        retryAfter: wait,
        retryable: true,
      };
    case "live_busy":
      return { text: "Live agency data is busy.", retryAfter: wait, retryable: true };
    case "live_data_unconfigured":
      return {
        text: "Live agency data is not available on this server. The snapshot views still work.",
        retryAfter: null,
        retryable: false,
      };
    case "upstream_timeout":
    case "upstream_error":
    case "upstream_bad_response":
    case "upstream_auth":
      return {
        text: "The FBI data service did not answer correctly. The snapshot views still work.",
        retryAfter: wait,
        retryable: err.code !== "upstream_auth",
      };
    case "warehouse_unavailable":
      return { text: "The data warehouse is not available.", retryAfter: null, retryable: true };
  }
  if (err.status === 404 || err.status === 422) {
    return { text: "There is no data for this selection.", retryAfter: null, retryable: false };
  }
  return {
    text: `The request failed (${err.status}).`,
    retryAfter: wait,
    retryable: err.status >= 500,
  };
}
