import { lazy, Suspense, useState } from "react";
import { Controls } from "./components/Controls";
import { Empty } from "./components/Empty";
import { Nav, type NavItem } from "./components/Nav";
import { NavDrawer } from "./components/NavDrawer";
import { Provenance } from "./components/Provenance";
import { TopBar } from "./components/TopBar";
import { useMeta } from "./lib/queries";
import { ReleaseContext } from "./lib/release";
import { useUrlState } from "./lib/urlState";

// Each view is its own chunk, so the first load fetches only the open view.
const HateCrimeView = lazy(() =>
  import("./views/HateCrimeView").then((m) => ({ default: m.HateCrimeView })),
);
const HomicideView = lazy(() =>
  import("./views/HomicideView").then((m) => ({ default: m.HomicideView })),
);
const LesdcView = lazy(() => import("./views/LesdcView").then((m) => ({ default: m.LesdcView })));
const NibrsEstimationView = lazy(() =>
  import("./views/NibrsEstimationView").then((m) => ({ default: m.NibrsEstimationView })),
);
const NibrsView = lazy(() => import("./views/NibrsView").then((m) => ({ default: m.NibrsView })));
const OverviewView = lazy(() =>
  import("./views/OverviewView").then((m) => ({ default: m.OverviewView })),
);
const PerformanceView = lazy(() =>
  import("./views/PerformanceView").then((m) => ({ default: m.PerformanceView })),
);
const PropertyView = lazy(() =>
  import("./views/PropertyView").then((m) => ({ default: m.PropertyView })),
);
const MethodologyView = lazy(() =>
  import("./views/MethodologyView").then((m) => ({ default: m.MethodologyView })),
);
const UseOfForceView = lazy(() =>
  import("./views/UseOfForceView").then((m) => ({ default: m.UseOfForceView })),
);

// Top-level views. Each domain group adds an entry here and a branch in the
// render switch below.
const VIEWS: NavItem[] = [
  { id: "overview", label: "Overview" },
  { id: "performance", label: "Performance" },
  { id: "hate-crime", label: "Hate Crime" },
  { id: "homicide", label: "Homicide" },
  { id: "property", label: "Property" },
  { id: "nibrs", label: "NIBRS" },
  { id: "nibrs-estimation", label: "NIBRS Est." },
  { id: "use-of-force", label: "Use of Force" },
  { id: "lesdc", label: "LESDC" },
  { id: "methodology", label: "Methodology" },
];

// Views with their own controls / no geography don't use the shared region bar.
const NO_REGION_VIEWS = new Set(["lesdc", "use-of-force", "nibrs-estimation", "methodology"]);

export default function App() {
  const meta = useMeta();
  const offenses = meta.data?.offenses ?? [];
  const states = meta.data?.states ?? [];
  // View, region, offense, agency and comparison live in the URL (shareable,
  // and back/forward work). Values that the snapshot does not have fall back.
  const [url, setUrl] = useUrlState();
  const [navOpen, setNavOpen] = useState(false);
  const known = meta.isSuccess;
  const view = VIEWS.some((v) => v.id === url.view) ? url.view : "overview";
  const region = !known || url.region === "US" || states.includes(url.region) ? url.region : "US";
  const active = offenses.includes(url.offense) ? url.offense : (offenses[0] ?? url.offense);
  const compare =
    url.compare && (!known || states.includes(url.compare)) && url.compare !== region
      ? url.compare
      : null;
  // An agency belongs to its state: a state view drops an agency of another state.
  const agency =
    url.agency && (region === "US" || url.agency.startsWith(region)) ? url.agency : null;
  const offenseRow = view === "overview" || view === "performance";
  const setView = (id: string) => setUrl({ view: id });
  const setRegion = (r: string) => setUrl({ region: r });
  const setOffense = (o: string) => setUrl({ offense: o });

  return (
    <ReleaseContext.Provider value={meta.data?.snapshot ?? null}>
      <div className="flex min-h-screen flex-col lg:h-screen lg:overflow-hidden">
        <TopBar
          snapshot={meta.data?.snapshot}
          onMenuClick={() => setNavOpen(true)}
          menuOpen={navOpen}
        />
        <NavDrawer
          items={VIEWS}
          active={view}
          open={navOpen}
          onClose={() => setNavOpen(false)}
          onSelect={(id) => {
            setView(id);
            setNavOpen(false);
          }}
        />
        {/* One <main> landmark holds the filters and the view (a11y: every part of
          the page is in a landmark). */}
        <main className="flex min-h-0 flex-1 flex-col">
          {/* The controls, the footer and the default offense come from /api/meta.
            Show one loading panel until it answers, then render them together,
            so no part of the page moves when the data arrives (layout shift).
            On an error, render the page with the fallbacks. */}
          {meta.isPending ? (
            <ViewLoading />
          ) : (
            <>
              {/* Below lg the inline Nav is hidden; for views without a region/offense
          bar the whole row would be empty, so hide it on mobile in that case. */}
              <div
                className={`panel brackets enter mx-3 mt-3 flex-wrap items-center gap-2 px-4 py-2.5 lg:flex lg:gap-4 ${
                  NO_REGION_VIEWS.has(view) ? "hidden" : "flex"
                }`}
              >
                <Nav items={VIEWS} active={view} onSelect={setView} />
                {!NO_REGION_VIEWS.has(view) && (
                  <>
                    {/* On desktop, the offense buttons always go on their own line.
                      The layout then does not depend on the number of offenses. */}
                    {offenseRow ? (
                      <span className="hidden lg:block lg:h-0 lg:basis-full" aria-hidden="true" />
                    ) : (
                      <span className="hidden h-4 w-px bg-line lg:block" />
                    )}
                    <Controls
                      offenses={offenses}
                      value={active}
                      onChange={setOffense}
                      states={states}
                      region={region}
                      onRegionChange={setRegion}
                      showOffenses={offenseRow}
                    />
                  </>
                )}
              </div>
              <Suspense fallback={<ViewLoading />}>
                {view === "overview" && (
                  <OverviewView
                    offense={active}
                    region={region}
                    agency={agency}
                    onAgencyChange={(ori) => setUrl({ agency: ori })}
                    compare={compare}
                    onCompareChange={(st) => setUrl({ compare: st })}
                  />
                )}
                {view === "performance" && <PerformanceView offense={active} region={region} />}
                {view === "hate-crime" && <HateCrimeView region={region} />}
                {view === "homicide" && <HomicideView region={region} />}
                {view === "property" && <PropertyView region={region} />}
                {view === "nibrs" && <NibrsView region={region} />}
                {view === "nibrs-estimation" && <NibrsEstimationView />}
                {view === "use-of-force" && <UseOfForceView />}
                {view === "lesdc" && <LesdcView />}
                {view === "methodology" && <MethodologyView />}
              </Suspense>
            </>
          )}
        </main>
        <Provenance snapshot={meta.data?.snapshot} view={view} />
      </div>
    </ReleaseContext.Provider>
  );
}

function ViewLoading() {
  return (
    <div className="flex flex-1 p-3" aria-busy="true">
      <div className="panel brackets flex-1">
        <Empty state={{ isLoading: true, isError: false }} />
      </div>
    </div>
  );
}
