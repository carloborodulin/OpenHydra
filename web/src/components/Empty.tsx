import { useEffect, useState } from "react";
import { describeError } from "../lib/errors";

interface QueryLike {
  isLoading: boolean;
  isError: boolean;
  error?: unknown;
  refetch?: () => unknown;
}

/** Seconds left until `until` (ms epoch), updated every second. */
function useCountdown(until: number | null): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (until == null) return;
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, [until]);
  return until == null ? 0 : Math.max(0, Math.ceil((until - now) / 1000));
}

// The placeholder of a panel without a chart. It tells apart:
// - loading (a skeleton),
// - an error, with what failed, what still works, and a Retry button that
//   waits for the API's Retry-After,
// - a valid but empty result (sparse data or an unsupported scope).
export function Empty({ state, message }: { state: QueryLike; message?: string }) {
  if (state.isLoading) {
    return (
      <div className="flex h-full flex-col justify-center gap-2 px-2" aria-busy="true">
        <span className="sr-only">Loading</span>
        {[80, 60, 70, 45].map((w, i) => (
          <div
            key={i}
            aria-hidden
            className="h-2.5 animate-pulse rounded bg-line motion-reduce:animate-none"
            style={{ width: `${w}%` }}
          />
        ))}
      </div>
    );
  }
  if (state.isError) return <ErrorState state={state} />;
  return (
    <div className="mono flex h-full items-center justify-center px-4 text-center text-[0.7rem] tracking-widest text-muted uppercase">
      {message ?? "No data for this selection"}
    </div>
  );
}

function ErrorState({ state }: { state: QueryLike }) {
  const view = describeError(state.error);
  const [until] = useState(() => (view.retryAfter ? Date.now() + view.retryAfter * 1000 : null));
  const left = useCountdown(until);
  return (
    <div
      role="alert"
      className="mono flex h-full flex-col items-center justify-center gap-2 px-4 text-center text-[0.7rem] text-muted"
    >
      <span>{view.text}</span>
      {view.retryable && state.refetch && (
        <button
          type="button"
          disabled={left > 0}
          onClick={() => state.refetch?.()}
          className="cursor-pointer border border-line-strong px-3 py-1 text-[0.65rem] tracking-wider text-accent uppercase disabled:cursor-not-allowed disabled:opacity-60"
        >
          {left > 0 ? `Retry in ${left}s` : "Retry"}
        </button>
      )}
    </div>
  );
}
