import { useMemo, useState } from "react";
import { Controls } from "./components/Controls";
import { MapPanel } from "./components/MapPanel";
import { Panel } from "./components/Panel";
import { StatTile } from "./components/StatTile";
import { TopBar } from "./components/TopBar";
import { ArrestsChart } from "./components/charts/ArrestsChart";
import { ClearanceChart } from "./components/charts/ClearanceChart";
import { PoliceEmploymentChart } from "./components/charts/PoliceEmploymentChart";
import { TrendChart } from "./components/charts/TrendChart";
import { fmtNum, fmtPct, fmtRate, lastNonNull, monthLabel, titleCase } from "./lib/format";
import { regionName } from "./lib/states";
import {
  useAgencies,
  useAgencyArrests,
  useAgencyOffenseMonthly,
  useAgencyPoliceEmployment,
  useArrests,
  useMeta,
  useOffenseMonthly,
  usePoliceEmployment,
} from "./lib/queries";

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
  const states = meta.data?.states ?? [];
  const [offense, setOffense] = useState("homicide");
  const [region, setRegion] = useState("US"); // "US" = national
  // When set, the trend/clearance/arrests/PE panels drill into one department
  // (served live by the backend); the map still shows the region's agencies.
  const [selectedAgency, setSelectedAgency] = useState<{ ori: string; name: string } | null>(
    null,
  );
  const active = offenses.includes(offense) ? offense : (offenses[0] ?? offense);

  const isNational = region === "US";
  const level = isNational ? "national" : "state";
  const area = region;
  const regionLabel = regionName(region);
  // Picking a region clears any drilled-in agency.
  const selectRegion = (r: string) => {
    setRegion(r);
    setSelectedAgency(null);
  };

  // Region-level (warehouse) and agency-level (live) sources; the agency hooks
  // stay disabled until an agency is selected. Display whichever is active.
  const ori = selectedAgency?.ori;
  const monthlyRegion = useOffenseMonthly(active, level, area);
  const raceRegion = useArrests("Arrestee Race", active, level, area);
  const peRegion = usePoliceEmployment(level, area);
  const monthlyAgency = useAgencyOffenseMonthly(ori, active);
  const raceAgency = useAgencyArrests(ori, "Arrestee Race", active);
  const peAgency = useAgencyPoliceEmployment(ori);

  const monthly = selectedAgency ? monthlyAgency : monthlyRegion;
  const race = selectedAgency ? raceAgency : raceRegion;
  const pe = selectedAgency ? peAgency : peRegion;
  const agencies = useAgencies(isNational ? undefined : region);
  const focusLabel = selectedAgency ? selectedAgency.name : regionLabel;

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
  const hasPe = (pe.data ?? []).some((r) => r.value != null);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopBar window={win} />
      <main
        className="grid min-h-0 flex-1 grid-cols-12 gap-3 p-3"
        style={{ gridTemplateRows: "auto auto minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)" }}
      >
        <section className="panel brackets enter col-span-12 flex items-center gap-4 px-4 py-2.5">
          <Controls
            offenses={offenses}
            value={active}
            onChange={setOffense}
            states={states}
            region={region}
            onRegionChange={selectRegion}
          />
          {selectedAgency && (
            <button
              type="button"
              onClick={() => setSelectedAgency(null)}
              title={`Exit ${selectedAgency.name}`}
              className="mono glow ml-auto shrink-0 cursor-pointer border border-accent bg-[rgba(34,211,238,0.1)] px-2.5 py-1 text-[0.62rem] tracking-wider text-accent uppercase transition hover:border-line-strong"
            >
              ← {regionLabel} · ✕ {selectedAgency.name}
            </button>
          )}
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
            label={`Agencies · ${region}`}
            accent="good"
            value={fmtNum(ag.length)}
            sub={`${nibrs} NIBRS · ${nibrsPct}%`}
          />
        </div>

        <Panel
          title={`Offense Rate · ${titleCase(active)} · ${focusLabel}`}
          className="col-span-8 col-start-1 row-start-3"
        >
          {rows.length ? <TrendChart data={rows} /> : <Empty state={monthly} />}
        </Panel>

        <Panel
          title={`Agency Network · ${regionLabel}`}
          right={<Legend />}
          className="col-span-4 col-start-9 row-start-3 row-span-3"
          bodyClass="relative overflow-hidden p-0"
        >
          {ag.length ? (
            <MapPanel
              agencies={ag}
              onSelectAgency={(ori, name) => setSelectedAgency({ ori, name })}
            />
          ) : (
            <Empty state={agencies} />
          )}
        </Panel>

        <Panel
          title={`Clearance Ratio · ${titleCase(active)}`}
          className="col-span-4 col-start-1 row-start-4"
        >
          {rows.length ? <ClearanceChart data={rows} /> : <Empty state={monthly} />}
        </Panel>

        <Panel
          title={`Arrests by Race · ${titleCase(active)} · ${focusLabel}`}
          className="col-span-4 col-start-5 row-start-4"
        >
          {race.data?.length ? <ArrestsChart data={race.data} /> : <Empty state={race} />}
        </Panel>

        <Panel
          title={`Police Employment · ${focusLabel}`}
          className="col-span-8 col-start-1 row-start-5"
        >
          {hasPe ? <PoliceEmploymentChart data={pe.data ?? []} /> : <Empty state={pe} />}
        </Panel>
      </main>
    </div>
  );
}
