import { useState } from "react";
import { Controls } from "./components/Controls";
import { Nav, type NavItem } from "./components/Nav";
import { TopBar } from "./components/TopBar";
import { useMeta } from "./lib/queries";
import { OverviewView } from "./views/OverviewView";

// Top-level views. Each domain group (Hate Crime, Homicide, …) adds an entry
// here and a branch in the render switch below.
const VIEWS: NavItem[] = [{ id: "overview", label: "Overview" }];

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
        <span className="h-4 w-px bg-line" />
        <Controls
          offenses={offenses}
          value={active}
          onChange={setOffense}
          states={states}
          region={region}
          onRegionChange={setRegion}
        />
      </div>
      {view === "overview" && <OverviewView offense={active} region={region} />}
    </div>
  );
}
