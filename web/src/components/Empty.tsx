// Shared placeholder for a panel whose query is loading, errored, or empty.
export function Empty({
  state,
  message,
}: {
  state: { isLoading: boolean; isError: boolean };
  /** Shown instead of "No Data" when the panel knows why it is empty. */
  message?: string;
}) {
  const label = state.isError
    ? "Signal Lost"
    : state.isLoading
      ? "Acquiring…"
      : (message ?? "No Data");
  return (
    <div className="mono flex h-full items-center justify-center text-[0.7rem] tracking-widest text-muted uppercase">
      {label}
    </div>
  );
}
