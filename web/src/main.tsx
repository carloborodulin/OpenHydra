import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import { ApiError } from "./lib/api";
import { ThemeProvider } from "./lib/ThemeProvider.tsx";
import "./index.css";

// Retry once, and only when a retry can help: not a 4xx (bad input, unknown
// agency, per-client limit) and not a spent upstream quota.
const NO_RETRY_CODES = new Set([
  "upstream_rate_limited",
  "live_budget_spent",
  "live_data_unconfigured",
]);
const retry = (count: number, err: unknown) =>
  count < 1 &&
  !(err instanceof ApiError && (err.status < 500 || NO_RETRY_CODES.has(err.code ?? "")));

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 60_000, refetchOnWindowFocus: false, retry } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
);
