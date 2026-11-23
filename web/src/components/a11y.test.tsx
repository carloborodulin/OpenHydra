import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import axe from "axe-core";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import type { AgencyFeature } from "../lib/api";
import { AgencySearch } from "./AgencySearch";
import { NavDrawer } from "./NavDrawer";
import { Select } from "./Select";

async function axeViolations(node: Element) {
  // Contrast needs real layout and "region" judges a whole page: the browser
  // test checks both. Here axe checks roles, names and states.
  const result = await axe.run(node, {
    rules: { "color-contrast": { enabled: false }, region: { enabled: false } },
  });
  return result.violations.map((v) => `${v.id}: ${v.nodes.length}`);
}

const ITEMS = [
  { id: "overview", label: "Overview" },
  { id: "homicide", label: "Homicide" },
  { id: "property", label: "Property" },
];

function DrawerHarness() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>
        Menu
      </button>
      <NavDrawer
        items={ITEMS}
        active="homicide"
        open={open}
        onClose={() => setOpen(false)}
        onSelect={() => setOpen(false)}
      />
    </>
  );
}

describe("NavDrawer", () => {
  it("keeps closed controls out of the tab order", async () => {
    render(<DrawerHarness />);
    const user = userEvent.setup();
    await user.tab();
    expect(screen.getByRole("button", { name: "Menu" })).toHaveFocus();
    // The closed drawer is inert, so Tab cannot reach its buttons. jsdom does not
    // implement inert, so this test checks the attribute; the browser test
    // checks the tab order.
    const drawer = document.getElementById("nav-drawer")?.parentElement;
    expect(drawer).toHaveAttribute("inert");
    expect(await axeViolations(document.body)).toEqual([]);
  });

  it("moves focus in, traps Tab, closes on Escape and restores focus", async () => {
    render(<DrawerHarness />);
    const user = userEvent.setup();
    const menu = screen.getByRole("button", { name: "Menu" });
    await user.click(menu);
    const dialog = screen.getByRole("dialog", { name: "Views" });
    const close = within(dialog).getByRole("button", { name: "Close navigation" });
    expect(close).toHaveFocus();
    expect(within(dialog).getByRole("button", { name: "Homicide" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await user.tab({ shift: true }); // wraps from the first to the last control
    expect(within(dialog).getByRole("button", { name: "Property" })).toHaveFocus();
    await user.tab(); // and from the last back to the first
    expect(close).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(menu).toHaveFocus();
  });
});

function SelectHarness() {
  const [v, setV] = useState("US");
  return (
    <Select
      value={v}
      onChange={setV}
      title="Region"
      options={[{ value: "US", label: "National" }]}
      groups={[
        {
          label: "States",
          options: [
            { value: "CA", label: "California" },
            { value: "NY", label: "New York" },
            { value: "NV", label: "Nevada" },
          ],
        },
      ]}
    />
  );
}

describe("Select", () => {
  it("works with the keyboard (arrows, type-ahead, Enter, Escape)", async () => {
    render(<SelectHarness />);
    const user = userEvent.setup();
    const box = screen.getByRole("combobox", { name: /^Region:/ });
    await user.tab();
    expect(box).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    expect(box).toHaveAttribute("aria-expanded", "true");
    const list = screen.getByRole("listbox", { name: "Region" });
    expect(within(list).getByRole("group", { name: "States" })).toBeInTheDocument();
    await user.keyboard("{ArrowDown}{Enter}");
    expect(box).toHaveTextContent("California");
    expect(box).toHaveFocus();
    await user.keyboard("{ArrowDown}");
    await user.keyboard("nev"); // type-ahead: the first label that starts with "nev"
    const active = box.getAttribute("aria-activedescendant");
    expect(document.getElementById(active as string)).toHaveTextContent("Nevada");
    await user.keyboard("{Escape}");
    expect(box).toHaveAttribute("aria-expanded", "false");
    expect(box).toHaveTextContent("California");
    await user.keyboard("{End}{Enter}");
    expect(box).toHaveTextContent("Nevada");
    expect(await axeViolations(document.body)).toEqual([]);
  });
});

const AGENCIES: AgencyFeature[] = [
  ["NY0303000", "Buffalo Police Department", "ERIE"],
  ["NY0303100", "Amherst Town Police", "ERIE"],
  ["CA0194200", "Los Angeles Police Department", "LOS ANGELES"],
].map(([ori, agency_name, county]) => ({
  ori,
  agency_name,
  county,
  agency_type: "City",
  state_abbr: ori.slice(0, 2),
  latitude: 1,
  longitude: 1,
  is_nibrs: true,
  nibrs_start_year: 2020,
}));

describe("AgencySearch", () => {
  it("finds and opens an agency without the map", async () => {
    const picked: string[] = [];
    render(<AgencySearch agencies={AGENCIES} onSelect={(ori) => picked.push(ori)} />);
    const user = userEvent.setup();
    const input = screen.getByRole("combobox", { name: /find an agency/i });
    await user.type(input, "erie");
    expect(screen.getAllByRole("option")).toHaveLength(2);
    await user.keyboard("{ArrowDown}{Enter}");
    expect(picked).toEqual(["NY0303100"]);
    expect(await axeViolations(document.body)).toEqual([]);
  });
});
