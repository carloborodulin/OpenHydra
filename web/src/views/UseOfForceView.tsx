import { useState } from "react";
import { Empty } from "../components/Empty";
import { Panel } from "../components/Panel";
import { StatTile } from "../components/StatTile";
import { ArrestsChart } from "../components/charts/ArrestsChart";
import { fmtNum } from "../lib/format";
import { useUofParticipation, useUofQuestions } from "../lib/queries";
import { hudBtn } from "../lib/ui";

const YEARS = [2019, 2020, 2021, 2022, 2023];

// uof/questions `quest` groups → friendly panel labels.
const QUESTS: { key: string; label: string }[] = [
  { key: "report", label: "Report Metrics" },
  { key: "force", label: "Type of Force" },
  { key: "means", label: "Means of Resistance" },
  { key: "contact", label: "Reason for Contact" },
];

export function UseOfForceView() {
  const [year, setYear] = useState(2022);
  const participation = useUofParticipation();
  const questions = useUofQuestions(year);

  return (
    <>
      <div className="mx-3 mt-3 flex flex-wrap items-center gap-3">
        <span className="panel-title shrink-0">Use of Force · Year</span>
        <div className="flex flex-wrap gap-1.5">
          {YEARS.map((y) => (
            <button key={y} type="button" onClick={() => setYear(y)} className={hudBtn(y === year)}>
              {y}
            </button>
          ))}
        </div>
      </div>

      {/* National reporting participation, one tile per year. */}
      <div className="mx-3 mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {(participation.data ?? []).map((p) => (
          <StatTile
            key={p.year}
            label={`${p.year} Participation`}
            accent={p.year === year ? "accent" : "good"}
            value={`${Math.round(p.participation_percent ?? 0)}%`}
            sub={`${fmtNum(p.participating_agencies)} / ${fmtNum(p.total_agencies)} agencies`}
          />
        ))}
      </div>

      <main className="grid flex-1 grid-cols-1 gap-3 p-3 [grid-auto-rows:minmax(240px,auto)] sm:grid-cols-2 lg:min-h-0 lg:grid-cols-12 lg:overflow-auto lg:[grid-auto-rows:minmax(240px,1fr)]">
        {QUESTS.map((qd) => {
          const data = (questions.data ?? []).filter((r) => r.category === qd.key);
          return (
            <Panel key={qd.key} title={`${qd.label} · ${year}`} className="col-span-1 lg:col-span-6">
              {data.length ? <ArrestsChart data={data} /> : <Empty state={questions} />}
            </Panel>
          );
        })}
      </main>
    </>
  );
}
