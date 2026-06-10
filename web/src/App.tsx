import { useState } from "react";
import { Controls } from "./components/Controls";
import { Nav, type NavItem } from "./components/Nav";
import { TopBar } from "./components/TopBar";
import { useMeta } from "./lib/queries";
import { HateCrimeView } from "./views/HateCrimeView";
import { HomicideView } from "./views/HomicideView";
import { LesdcView } from "./views/LesdcView";
import { NibrsView } from "./views/NibrsView";
import { OverviewView } from "./views/OverviewView";
import { PropertyView } from "./views/PropertyView";

// Top-level views. Each domain group (Use of Force, …) adds an entry here and a
// branch in the render switch below.
const VIEWS: NavItem[] = [
  { id: "overview", label: "Overview" },
  { id: "hate-crime", label: "Hate Crime" },
  { id: "homicide", label: "Homicide" },
  { id: "property", label: "Property" },
  { id: "nibrs", label: "NIBRS" },
  { id: "lesdc", label: "LESDC" },
];

// Views with their own controls / no geography don't use the shared region bar.
const NO_REGION_VIEWS = new Set(["lesdc"]);

export default function App() {
  const meta = useMeta();
  const offenses = meta.data?.offenses ?? [];
  const states = meta.data?.states ?? [];
  const [offense, setOffense] = useState("homicide");
  const [region, setRegion] = useState("US"); // "US" = national
  const [view, setView] = useState("overview");

  const active = offenses.includes(offense) ? offense : (offenses[0] ?? offense);

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <TopBar />
      <div className="panel brackets enter mx-3 mt-3 flex flex-wrap items-center gap-4 px-4 py-2.5">
        <Nav items={VIEWS} active={view} onSelect={setView} />
        {!NO_REGION_VIEWS.has(view) && (
          <>
            <span className="h-4 w-px bg-line" />
            <Controls
              offenses={offenses}
              value={active}
              onChange={setOffense}
              states={states}
              region={region}
              onRegionChange={setRegion}
              showOffenses={view === "overview"}
            />
          </>
        )}
      </div>
      {view === "overview" && <OverviewView offense={active} region={region} />}
      {view === "hate-crime" && <HateCrimeView region={region} />}
      {view === "homicide" && <HomicideView region={region} />}
      {view === "property" && <PropertyView region={region} />}
      {view === "nibrs" && <NibrsView region={region} />}
      {view === "lesdc" && <LesdcView />}
    </div>
  );
}
