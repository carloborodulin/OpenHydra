// Shared placeholder for a panel whose query is loading, errored, or empty.
export function Empty({ state }: { state: { isLoading: boolean; isError: boolean } }) {
  const label = state.isError ? "Signal Lost" : state.isLoading ? "Acquiring…" : "No Data";
  return (
    <div className="mono flex h-full items-center justify-center text-[0.7rem] tracking-widest text-muted uppercase">
      {label}
    </div>
  );
}
