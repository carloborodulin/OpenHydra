import { useState } from "react";
import { Empty } from "../components/Empty";
import { Panel } from "../components/Panel";
import { StatTile } from "../components/StatTile";
import { HBarChart } from "../components/charts/HBarChart";
import { count } from "../lib/measures";
import { participationFacts } from "../lib/participation";
import { useUofParticipation, useUofQuestions } from "../lib/queries";
import { hudBtn } from "../lib/ui";

// The FBI page that defines the Use-of-Force collection and its participation measure.
const UOF_METHOD_URL =
  "https://www.fbi.gov/how-we-can-help-you/more-fbi-services-and-information/ucr/use-of-force";

// uof/questions `quest` groups → friendly panel labels.
const QUESTS: { key: string; label: string }[] = [
  { key: "report", label: "Report Metrics" },
  { key: "force", label: "Type of Force" },
  { key: "means", label: "Means of Resistance" },
  { key: "contact", label: "Reason for Contact" },
];

export function UseOfForceView() {
  const participation = useUofParticipation();
  const years = (participation.data ?? []).map((p) => p.year);
  const [picked, setYear] = useState<number | null>(null);
  // Default to the latest year in the snapshot.
  const year = picked ?? (years.length ? Math.max(...years) : 2022);
  const questions = useUofQuestions(year);

  return (
    <>
      <div className="mx-3 mt-3 flex flex-wrap items-center gap-3">
        <span className="panel-title shrink-0">Use of Force · Year</span>
        <div className="flex flex-wrap gap-1.5">
          {years.map((y) => (
            <button key={y} type="button" onClick={() => setYear(y)} className={hudBtn(y === year)}>
              {y}
            </button>
          ))}
        </div>
      </div>

      {/* National participation, one tile per year. The big value is the FBI's
          own measure; the agency share under it has a different denominator. */}
      <div className="mx-3 mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {(participation.data ?? []).map((p) => {
          const f = participationFacts(p);
          return (
            <StatTile
              key={p.year}
              label={`${p.year} · FBI participation`}
              accent={p.year === year ? "accent" : "good"}
              value={f.fbiPercent}
              sub={`Agencies ${f.agencyShare} · ${f.agencyLine}`}
            />
          );
        })}
      </div>
      <p className="mono mx-3 mt-2 text-[0.62rem] leading-relaxed text-muted">
        Two measures with different denominators. The large value is the FBI participation
        figure, which the FBI states as the share of sworn officers that the participating
        agencies employ. The agency share is participating agencies ÷ all agencies. A dash
        means that the FBI reports no value.{" "}
        <a className="text-accent underline" href={UOF_METHOD_URL} target="_blank" rel="noreferrer">
          FBI method
        </a>
      </p>

      <div className="grid flex-1 grid-cols-1 gap-3 p-3 [grid-auto-rows:minmax(240px,auto)] sm:grid-cols-2 lg:min-h-0 lg:grid-cols-12 lg:overflow-auto lg:[grid-auto-rows:minmax(240px,1fr)]">
        {QUESTS.map((qd) => {
          const data = (questions.data ?? []).filter((r) => r.category === qd.key);
          return (
            <Panel key={qd.key} title={`${qd.label} · ${year}`} className="col-span-1 lg:col-span-6">
              {data.length ? (
                <HBarChart data={data} measure={count("Incidents")} label={`${qd.label}, ${year}`} />
              ) : (
                <Empty state={questions} />
              )}
            </Panel>
          );
        })}
      </div>
    </>
  );
}
