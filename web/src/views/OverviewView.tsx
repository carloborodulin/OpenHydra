import { useMemo, useState } from "react";
import { MapPanel } from "../components/MapPanel";
import { Panel } from "../components/Panel";
import { StatTile } from "../components/StatTile";
import { ArrestsChart } from "../components/charts/ArrestsChart";
import { ClearanceChart } from "../components/charts/ClearanceChart";
import { PoliceEmploymentChart } from "../components/charts/PoliceEmploymentChart";
import { TrendChart } from "../components/charts/TrendChart";
import type { ArrestOffense } from "../lib/api";
import { fmtNum, fmtPct, fmtRate, lastNonNull, monthLabel, titleCase } from "../lib/format";
import {
  useAgencies,
  useAgencyArrests,
  useAgencyOffenseMonthly,
  useAgencyPoliceEmployment,
  useArrests,
  useMeta,
  useOffenseMonthly,
  usePoliceEmployment,
} from "../lib/queries";
import { regionName } from "../lib/states";

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
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: "#3df5b0", boxShadow: "0 0 6px #3df5b0" }}
        />
        NIBRS
      </span>
      <span className="flex items-center gap-1">
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{ background: "#ff5470", boxShadow: "0 0 6px #ff5470" }}
        />
        SRS
      </span>
    </div>
  );
}

const SELECT =
  "mono max-w-[8rem] cursor-pointer border border-line bg-[rgba(34,211,238,0.06)] px-1.5 py-0.5 text-[0.6rem] tracking-wider text-accent uppercase transition hover:border-line-strong focus:border-accent focus:outline-none";

export function OverviewView({ offense, region }: { offense: string; region: string }) {
  const meta = useMeta();
  const arrestCats = meta.data?.arrest_categories?.length
    ? meta.data.arrest_categories
    : ["Arrestee Race"];

  // Drill into one department (served live by the backend); the map still shows
  // the region's agencies.
  const [selectedAgency, setSelectedAgency] = useState<{ ori: string; name: string } | null>(null);
  // Arrests panel has its own dimension controls. arrestOffense "" = follow the
  // main offense selector; otherwise an arrest-specific offense (48-code taxonomy).
  const [arrestOffense, setArrestOffense] = useState("");
  const [arrestCategory, setArrestCategory] = useState("Arrestee Race");

  const isNational = region === "US";
  const level = isNational ? "national" : "state";
  const area = region;
  const regionLabel = regionName(region);

  const ori = selectedAgency?.ori;
  const arrestOff = arrestOffense || offense; // "" => follow the main offense

  // Region-level (warehouse) and agency-level (live) sources; agency hooks stay
  // disabled until an agency is selected. Display whichever is active.
  const monthlyRegion = useOffenseMonthly(offense, level, area);
  const arrestsRegion = useArrests(arrestCategory, arrestOff, level, area);
  const peRegion = usePoliceEmployment(level, area);
  const monthlyAgency = useAgencyOffenseMonthly(ori, offense);
  const arrestsAgency = useAgencyArrests(ori, arrestCategory, arrestOff);
  const peAgency = useAgencyPoliceEmployment(ori);

  const monthly = selectedAgency ? monthlyAgency : monthlyRegion;
  const arrests = selectedAgency ? arrestsAgency : arrestsRegion;
  const pe = selectedAgency ? peAgency : peRegion;
  const agencies = useAgencies(isNational ? undefined : region);
  const focusLabel = selectedAgency ? selectedAgency.name : regionLabel;

  const rows = useMemo(() => monthly.data ?? [], [monthly.data]);
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

  // Group the 48 arrest offenses by UCR category for the dropdown.
  const offenseGroups = useMemo(() => {
    const m = new Map<string, ArrestOffense[]>();
    for (const o of meta.data?.arrest_offenses ?? []) {
      const g = m.get(o.category) ?? [];
      g.push(o);
      m.set(o.category, g);
    }
    return [...m.entries()];
  }, [meta.data?.arrest_offenses]);

  return (
    <main
      className="grid min-h-0 flex-1 grid-cols-12 gap-3 p-3"
      style={{ gridTemplateRows: "auto minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr)" }}
    >
      <div className="col-span-3">
        <StatTile
          label="Latest Rate /100k"
          value={fmtRate(latestRate?.value)}
          sub={latestRate ? `${titleCase(offense)} · ${monthLabel(latestRate.period)}` : "—"}
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
        title={`Offense Rate · ${titleCase(offense)} · ${focusLabel}`}
        className="col-span-8 col-start-1 row-start-2"
      >
        {rows.length ? <TrendChart data={rows} /> : <Empty state={monthly} />}
      </Panel>

      <Panel
        title={`Agency Network · ${regionLabel}`}
        right={
          <div className="flex items-center gap-3">
            <Legend />
            {selectedAgency && (
              <button
                type="button"
                onClick={() => setSelectedAgency(null)}
                title={`Exit ${selectedAgency.name}`}
                className="mono glow cursor-pointer border border-accent bg-[rgba(34,211,238,0.1)] px-2 py-0.5 text-[0.58rem] tracking-wider text-accent uppercase transition hover:border-line-strong"
              >
                ✕ {selectedAgency.name}
              </button>
            )}
          </div>
        }
        className="col-span-4 col-start-9 row-start-2 row-span-3"
        bodyClass="relative overflow-hidden p-0"
      >
        {ag.length ? (
          <MapPanel agencies={ag} onSelectAgency={(o, name) => setSelectedAgency({ ori: o, name })} />
        ) : (
          <Empty state={agencies} />
        )}
      </Panel>

      <Panel
        title={`Clearance Ratio · ${titleCase(offense)}`}
        className="col-span-4 col-start-1 row-start-3"
      >
        {rows.length ? <ClearanceChart data={rows} /> : <Empty state={monthly} />}
      </Panel>

      <Panel
        title="Arrests"
        right={
          <div className="flex items-center gap-1.5">
            <select
              value={arrestCategory}
              onChange={(e) => setArrestCategory(e.target.value)}
              className={SELECT}
              title="Arrest demographic category"
            >
              {arrestCats.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
            <select
              value={arrestOffense}
              onChange={(e) => setArrestOffense(e.target.value)}
              className={SELECT}
              title="Arrest offense"
            >
              <option value="">Follow · {titleCase(offense)}</option>
              {offenseGroups.map(([cat, offs]) => (
                <optgroup key={cat} label={cat}>
                  {offs.map((o) => (
                    <option key={o.slug} value={o.slug}>
                      {o.name}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
        }
        className="col-span-4 col-start-5 row-start-3"
      >
        {arrests.data?.length ? <ArrestsChart data={arrests.data} /> : <Empty state={arrests} />}
      </Panel>

      <Panel title={`Police Employment · ${focusLabel}`} className="col-span-8 col-start-1 row-start-4">
        {hasPe ? <PoliceEmploymentChart data={pe.data ?? []} /> : <Empty state={pe} />}
      </Panel>
    </main>
  );
}
