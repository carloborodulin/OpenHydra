import { useMemo, useState } from "react";
import { AgencySearch } from "../components/AgencySearch";
import { DeltaIndicator } from "../components/DeltaIndicator";
import { Empty } from "../components/Empty";
import { MapPanel } from "../components/MapPanel";
import { Panel } from "../components/Panel";
import { Select } from "../components/Select";
import { StatTile } from "../components/StatTile";
import { HBarChart } from "../components/charts/HBarChart";
import { ARRESTS } from "../lib/measures";
import { ClearanceChart } from "../components/charts/ClearanceChart";
import { PoliceEmploymentChart } from "../components/charts/PoliceEmploymentChart";
import { TrendChart, type TrendMode } from "../components/charts/TrendChart";
import type { ArrestOffense } from "../lib/api";
import { fmtNum, fmtPct, fmtRate, lastNonNull, monthLabel, titleCase } from "../lib/format";
import {
  useAgencies,
  useAgencyArrests,
  useAgencyOffenseMonthly,
  useAgencyPoliceEmployment,
  useArrests,
  useArrestsAvailable,
  useMeta,
  useOffenseBenchmark,
  useOffenseMonthly,
  usePoliceEmployment,
} from "../lib/queries";
import { regionName } from "../lib/states";

const TREND_TITLES: Record<TrendMode, string> = {
  rate: "Offense Rate",
  index: "TTM index (Dec 2019 = 100)",
  relative: "Relative to National",
};

function Legend() {
  return (
    <div className="mono flex items-center gap-3 text-[0.55rem] tracking-wider text-muted uppercase">
      <span className="flex items-center gap-1">
        <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-accent" />
        NIBRS
      </span>
      <span className="flex items-center gap-1">
        <span
          aria-hidden
          className="inline-block h-2 w-2 rounded-full border-2 border-warn bg-transparent"
        />
        SRS
      </span>
    </div>
  );
}

export function OverviewView({
  offense,
  region,
  agency,
  onAgencyChange,
  compare,
  onCompareChange,
}: {
  offense: string;
  region: string;
  /** ORI of the drilled-in agency (from the URL), or null. */
  agency: string | null;
  onAgencyChange: (ori: string | null) => void;
  /** A second state for the trend overlay (from the URL), or null. */
  compare: string | null;
  onCompareChange: (state: string | null) => void;
}) {
  const meta = useMeta();
  const arrestCats = meta.data?.arrest_categories?.length
    ? meta.data.arrest_categories
    : ["Arrestee Race"];

  // Drill into one department (served live by the backend); the map still shows
  // the region's agencies.
  const isNational0 = region === "US";
  const agencies = useAgencies(isNational0 ? undefined : region);
  // The agency comes from the URL; its name from the agency list of the snapshot.
  const selectedAgency = useMemo(() => {
    if (!agency) return null;
    const hit = agencies.data?.find((a) => a.ori === agency);
    return { ori: agency, name: hit?.agency_name ?? agency };
  }, [agency, agencies.data]);
  const setSelectedAgency = (a: { ori: string } | null) => onAgencyChange(a?.ori ?? null);
  // Arrests panel has its own dimension controls. arrestOffense "" = follow the
  // main offense selector; otherwise an arrest-specific offense (48-code taxonomy).
  const [arrestOffense, setArrestOffense] = useState("");
  const [arrestCategory, setArrestCategory] = useState("Arrestee Race");
  // Trend panel view: raw monthly rate, 2019-indexed (de-seasonalized), or relative
  // to the national average. "relative" only applies when a state is selected.
  const [view, setView] = useState<TrendMode>("rate");

  const isNational = region === "US";
  const level = isNational ? "national" : "state";
  const area = region;
  const regionLabel = regionName(region);

  const ori = selectedAgency?.ori;
  const arrestOff = arrestOffense || offense; // "" => follow the main offense
  // A category picked in one scope may be absent in the next; fall back to the first.
  const arrestCat = arrestCats.includes(arrestCategory) ? arrestCategory : arrestCats[0];

  // Region-level (warehouse) and agency-level (live) sources; agency hooks stay
  // disabled until an agency is selected. Display whichever is active.
  const monthlyRegion = useOffenseMonthly(offense, level, area);
  // The comparison state (warehouse data), for the trend overlay only.
  const monthlyCompare = useOffenseMonthly(offense, "state", compare ?? "", Boolean(compare));
  // Benchmark vs national — only for a selected state, and only when not drilled
  // into a single (live) agency.
  const canBenchmark = !isNational && !selectedAgency;
  const benchmark = useOffenseBenchmark(offense, level, area, canBenchmark);
  // The snapshot holds a subset of the arrest taxonomy for each scope. The live
  // agency route serves every code, so the check applies only to the region.
  const available = useArrestsAvailable(level, area, !selectedAgency);
  const availableSet = useMemo(
    () => new Set(available.data?.offenses ?? []),
    [available.data?.offenses],
  );
  const arrestInScope = Boolean(selectedAgency) || availableSet.has(arrestOff);
  const arrestsRegion = useArrests(arrestCat, arrestOff, level, area);
  const peRegion = usePoliceEmployment(level, area);
  const monthlyAgency = useAgencyOffenseMonthly(ori, offense);
  const arrestsAgency = useAgencyArrests(ori, arrestCat, arrestOff);
  const peAgency = useAgencyPoliceEmployment(ori);

  const monthly = selectedAgency ? monthlyAgency : monthlyRegion;
  const arrests = selectedAgency ? arrestsAgency : arrestsRegion;
  const pe = selectedAgency ? peAgency : peRegion;
  const focusLabel = selectedAgency ? selectedAgency.name : regionLabel;

  const rows = useMemo(() => monthly.data ?? [], [monthly.data]);
  // The live badge shows only after a successful live answer, with its real range.
  const liveRange = useMemo(() => {
    if (!selectedAgency || !monthlyAgency.isSuccess) return null;
    const periods = (monthlyAgency.data ?? [])
      .filter((r) => r.offenses_actual != null)
      .map((r) => r.period);
    if (!periods.length) return null;
    return `${monthLabel(periods[0])} – ${monthLabel(periods[periods.length - 1])}`;
  }, [selectedAgency, monthlyAgency.isSuccess, monthlyAgency.data]);
  const latestRate = lastNonNull(rows, "offenses_rate");
  const latestYoy = lastNonNull(rows, "yoy_delta");
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

  // "relative" only applies to a state benchmark; agency drill-down has no
  // warehouse-derived series, so force the raw rate there.
  const effView: TrendMode = selectedAgency
    ? "rate"
    : !canBenchmark && view === "relative"
      ? "rate"
      : view;
  const benchRows = canBenchmark ? (benchmark.data ?? []) : [];
  const latestRel = lastNonNull(benchRows, "relative_index");

  const ag = agencies.data ?? [];
  const nibrs = ag.filter((a) => a.is_nibrs).length;
  const nibrsPct = ag.length ? Math.round((nibrs / ag.length) * 100) : 0;
  const hasPe = (pe.data ?? []).some((r) => r.value != null);

  // Group the arrest offenses by UCR category for the dropdown. A region view
  // offers only the offenses that have rows in the snapshot for that scope; an
  // agency view (live) offers every code.
  const offenseGroups = useMemo(() => {
    const m = new Map<string, ArrestOffense[]>();
    for (const o of meta.data?.arrest_offenses ?? []) {
      if (!selectedAgency && !availableSet.has(o.slug)) continue;
      const g = m.get(o.category) ?? [];
      g.push(o);
      m.set(o.category, g);
    }
    return [...m.entries()];
  }, [meta.data?.arrest_offenses, selectedAgency, availableSet]);
  // Leave a chosen offense that the new scope lacks: fall back to "follow".
  const arrestValue =
    arrestOffense && (selectedAgency || availableSet.has(arrestOffense)) ? arrestOffense : "";

  return (
    <div className="grid flex-1 grid-cols-1 gap-3 p-3 sm:grid-cols-2 lg:min-h-0 lg:grid-cols-12 lg:[grid-template-rows:auto_minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)]">
      <div className="col-span-1 lg:col-span-3">
        <StatTile
          label="Latest Rate /100k"
          value={fmtRate(latestRate?.value)}
          delta={<DeltaIndicator value={latestYoy?.value} />}
          sub={
            latestRate
              ? latestRel
                ? `${monthLabel(latestRate.period)} · ${(latestRel.value / 100).toFixed(1)}× US`
                : `${focusLabel} · ${monthLabel(latestRate.period)}`
              : "—"
          }
        />
      </div>
      <div className="col-span-1 lg:col-span-3">
        <StatTile
          label="Clearance"
          accent="warn"
          value={fmtPct(latestClr?.value)}
          sub={latestClr ? `${focusLabel} · ${monthLabel(latestClr.period)}` : "—"}
        />
      </div>
      <div className="col-span-1 lg:col-span-3">
        <StatTile
          label="Peak Rate /100k"
          accent="alert"
          value={fmtRate(peak?.value)}
          sub={peak ? `${focusLabel} · ${monthLabel(peak.period)}` : "—"}
        />
      </div>
      <div className="col-span-1 lg:col-span-3">
        <StatTile
          label={`Agencies · ${region}`}
          accent="good"
          value={fmtNum(ag.length)}
          sub={`${nibrs} NIBRS · ${nibrsPct}%`}
        />
      </div>

      <Panel
        title={`${TREND_TITLES[effView]} · ${titleCase(offense)} · ${focusLabel}`}
        right={
          !selectedAgency && rows.length ? (
            <div className="flex items-center gap-1.5">
              <Select
                value={compare ?? ""}
                onChange={(v) => onCompareChange(v || null)}
                options={[
                  { value: "", label: "Compare · none" },
                  ...(meta.data?.states ?? [])
                    .filter((s) => s !== region)
                    .map((s) => ({ value: s, label: `vs ${regionName(s)}` })),
                ]}
                title="Compare with a state"
                className="w-32"
              />
              <Select
                value={effView}
                onChange={(v) => setView(v as TrendMode)}
                options={[
                  { value: "rate", label: "Rate" },
                  { value: "index", label: "Index ’19" },
                  ...(canBenchmark ? [{ value: "relative", label: "vs National" }] : []),
                ]}
                title="Trend view"
                className="w-32"
              />
            </div>
          ) : undefined
        }
        className="col-span-full lg:col-span-8 lg:col-start-1 lg:row-start-2"
      >
        {rows.length ? (
          <TrendChart
            data={rows}
            mode={effView}
            benchmark={benchRows.length ? benchRows : undefined}
            compare={
              compare && !selectedAgency && monthlyCompare.data
                ? { label: regionName(compare), rows: monthlyCompare.data }
                : undefined
            }
          />
        ) : (
          <Empty state={monthly} />
        )}
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
                className="mono glow inline-flex min-h-12 cursor-pointer items-center border border-accent bg-accent/10 px-3 py-2.5 text-[0.62rem] tracking-wider text-accent uppercase transition hover:border-line-strong lg:min-h-0 lg:px-2 lg:py-0.5 lg:text-[0.58rem]"
              >
                ✕ {selectedAgency.name}
              </button>
            )}
            {selectedAgency && liveRange && (
              <span
                className="mono inline-flex items-center gap-1.5 text-[0.58rem] tracking-wider text-good uppercase"
                title="Agency data comes live from the FBI Crime Data Explorer API"
              >
                <span className="live-dot" aria-hidden />
                Live · {liveRange}
              </span>
            )}
          </div>
        }
        className="col-span-full lg:col-span-4 lg:col-start-9 lg:row-start-2 lg:row-span-3"
        bodyClass="relative overflow-hidden p-0"
      >
        {ag.length ? (
          <div className="flex h-full flex-col">
            <AgencySearch
              agencies={ag}
              onSelect={(o) => setSelectedAgency({ ori: o })}
            />
            <div className="min-h-0 flex-1">
              <MapPanel
                agencies={ag}
                onSelectAgency={(o) => setSelectedAgency({ ori: o })}
              />
            </div>
          </div>
        ) : (
          <Empty state={agencies} />
        )}
      </Panel>

      <Panel
        title={`Clearance Ratio · ${titleCase(offense)}`}
        className="col-span-full lg:col-span-4 lg:col-start-1 lg:row-start-3"
      >
        {rows.length ? <ClearanceChart data={rows} /> : <Empty state={monthly} />}
      </Panel>

      <Panel
        title="Arrests"
        right={
          <div className="flex items-center gap-1.5">
            <Select
              value={arrestCat}
              onChange={setArrestCategory}
              options={arrestCats.map((c) => ({ value: c, label: c }))}
              title="Arrest demographic category"
              className="w-32"
            />
            <Select
              value={arrestValue}
              onChange={setArrestOffense}
              options={[{ value: "", label: `Follow · ${titleCase(offense)}` }]}
              groups={offenseGroups.map(([cat, offs]) => ({
                label: cat,
                options: offs.map((o) => ({ value: o.slug, label: o.name })),
              }))}
              title="Arrest offense"
              className="w-36"
            />
          </div>
        }
        className="col-span-full lg:col-span-4 lg:col-start-5 lg:row-start-3"
      >
        {!arrestInScope && !available.isLoading ? (
          <Empty
            state={available}
            message={`No arrest data for ${titleCase(arrestOff)} in ${regionLabel}`}
          />
        ) : arrests.data?.length ? (
          <HBarChart
            data={arrests.data}
            measure={ARRESTS}
            label={`Arrests by ${arrestCat}, ${focusLabel}`}
          />
        ) : (
          <Empty state={arrests} />
        )}
      </Panel>

      <Panel
        title={`Police Employment · ${focusLabel}`}
        className="col-span-full lg:col-span-8 lg:col-start-1 lg:row-start-4"
      >
        {hasPe ? <PoliceEmploymentChart data={pe.data ?? []} /> : <Empty state={pe} />}
      </Panel>
    </div>
  );
}
