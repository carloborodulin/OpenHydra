import type { Snapshot } from "../lib/api";
import { viewCoverage } from "../lib/snapshot";

/** One line under each view: the source, the window and the extraction date. */
export function Provenance({ snapshot, view }: { snapshot?: Snapshot | null; view: string }) {
  if (!snapshot) return null;
  const { windows, days } = viewCoverage(snapshot, view);
  return (
    <footer className="mono mx-3 mb-3 px-1 text-[0.6rem] leading-relaxed tracking-wide text-muted lg:mt-auto">
      Source: FBI Crime Data Explorer API (Uniform Crime Reporting). Release{" "}
      <span className="text-ink">{snapshot.release_id}</span>
      {windows.length > 0 && <> · data {windows.join("; ")}</>}
      {days.length > 0 && (
        <>
          {" "}
          · extracted {days.join(", ")}
          {snapshot.reconstructed && " (dates from the project history)"}
        </>
      )}
      . The FBI revises past months; this snapshot does not change until the next release.
    </footer>
  );
}
