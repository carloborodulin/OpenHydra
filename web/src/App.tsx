import { useMemo, useState } from "react";
import { Controls } from "./components/Controls";
import { MapPanel } from "./components/MapPanel";
import { Panel } from "./components/Panel";
import { StatTile } from "./components/StatTile";
import { TopBar } from "./components/TopBar";
import { ArrestsChart } from "./components/charts/ArrestsChart";
import { ClearanceChart } from "./components/charts/ClearanceChart";
import { TrendChart } from "./components/charts/TrendChart";
import { fmtNum, fmtPct, fmtRate, lastNonNull, monthLabel, titleCase } from "./lib/format";
import { useAgencies, useArrests, useMeta, useOffenseMonthly } from "./lib/queries";

const MAP_STATE = "NY";

function Empty({ state }: { state: { isLoading: boolean; isError: boolean } }) {
  const label = state.isError ? "Signal Lost" : state.isLoading ? "Acquiring…" : "No Data";
  return (
    <div className="mono flex h-full items-center justify-center text-[0.7rem] tracking-widest text-muted uppercase">
      {label}
    </div>
  );
}

function Legend() {
  return (
    <div className="mono flex items-center gap-3 text-[0.55rem] tracking-wider text-muted uppercase">
      <span className="flex items-center gap-1">
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: "#3df5b0", boxShadow: "0 0 6px #3df5b0" }} />
        NIBRS
      </span>
      <span className="flex items-center gap-1">
        <span className="inline-block h-2 w-2 rounded-full" style={{ background: "#ff5470", boxShadow: "0 0 6px #ff5470" }} />
        SRS
      </span>
    </div>
  );
}

export default function App() {
  const meta = useMeta();
  const offenses = meta.data?.offenses ?? [];
  const [offense, setOffense] = useState("homicide");
  const active = offenses.includes(offense) ? offense : (offenses[0] ?? offense);

  const monthly = useOffenseMonthly(active);
  const race = useArrests("Arrestee Race");
  const agencies = useAgencies(MAP_STATE);

  const rows = useMemo(() => monthly.data ?? [], [monthly.data]);
  const win = rows.length
    ? `${monthLabel(rows[0].period)} – ${monthLabel(rows[rows.length - 1].period)}`
    : undefined;

  const latestRate = lastNonNull(rows, "offenses_rate");
  const latestClr = lastNonNull(rows, "clearance_ratio");
  const peak = useMemo(
    () =>
      rows.reduce<{ value: number; period: string } | null>(
        (best, r) =>
          r.offenses_rate != null && (!best || r.offenses_rate > best.value)
            ? { value: r.offenses_rate, period: r.period }
            : best,
        null,
      ),
    [rows],
  );

  const ag = agencies.data ?? [];
  const nibrs = ag.filter((a) => a.is_nibrs).length;
  const nibrsPct = ag.length ? Math.round((nibrs / ag.length) * 100) : 0;

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopBar window={win} />
      <main
        className="grid min-h-0 flex-1 grid-cols-12 gap-3 p-3"
        style={{ gridTemplateRows: "auto auto minmax(0, 1fr) minmax(0, 1fr)" }}
      >
        <section className="panel brackets enter col-span-12 flex items-center gap-4 px-4 py-2.5">
          <span className="panel-title shrink-0">Offense</span>
          <Controls offenses={offenses} value={active} onChange={setOffense} />
        </section>

        <div className="col-span-3">
          <StatTile
            label="Latest Rate /100k"
            value={fmtRate(latestRate?.value)}
            sub={latestRate ? `${titleCase(active)} · ${monthLabel(latestRate.period)}` : "—"}
          />
        </div>
        <div className="col-span-3">
          <StatTile
            label="Clearance"
            accent="warn"
            value={fmtPct(latestClr?.value)}
            sub={latestClr ? `Cleared · ${monthLabel(latestClr.period)}` : "—"}
          />
        </div>
        <div className="col-span-3">
          <StatTile
            label="Peak Rate /100k"
            accent="alert"
            value={fmtRate(peak?.value)}
            sub={peak ? monthLabel(peak.period) : "—"}
          />
        </div>
        <div className="col-span-3">
          <StatTile
            label={`Agencies · ${MAP_STATE}`}
            accent="good"
            value={fmtNum(ag.length)}
            sub={`${nibrs} NIBRS · ${nibrsPct}%`}
          />
        </div>

        <Panel
          title={`Offense Rate · ${titleCase(active)} · National`}
          className="col-span-8 col-start-1 row-start-3"
        >
          {rows.length ? <TrendChart data={rows} /> : <Empty state={monthly} />}
        </Panel>

        <Panel
          title={`Agency Network · ${MAP_STATE}`}
          right={<Legend />}
          className="col-span-4 col-start-9 row-start-3 row-span-2"
          bodyClass="relative overflow-hidden p-0"
        >
          {ag.length ? <MapPanel agencies={ag} /> : <Empty state={agencies} />}
        </Panel>

        <Panel
          title={`Clearance Ratio · ${titleCase(active)}`}
          className="col-span-4 col-start-1 row-start-4"
        >
          {rows.length ? <ClearanceChart data={rows} /> : <Empty state={monthly} />}
        </Panel>

        <Panel title="Arrests by Race · National" className="col-span-4 col-start-5 row-start-4">
          {race.data?.length ? <ArrestsChart data={race.data} /> : <Empty state={race} />}
        </Panel>
      </main>
    </div>
  );
}
