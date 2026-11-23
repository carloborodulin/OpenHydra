import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ReactElement } from "react";
import { count, dollars } from "../../lib/measures";
import { ThemeProvider } from "../../lib/ThemeProvider";
import { HBarChart } from "./HBarChart";

// ResponsiveContainer measures its parent; jsdom has no layout.
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver;

const renderThemed = (ui: ReactElement) => render(<ThemeProvider>{ui}</ThemeProvider>);

const rows = (pairs: [string, number | null][], category = "c") =>
  pairs.map(([label, value]) => ({ category, label, value }));

describe("HBarChart", () => {
  it("labels dollars as dollars, not arrests, and keeps every category in the table", () => {
    const data = rows([
      ["Firearms", 14479512996],
      ["Jewelry", 2500.5],
      ["Livestock", 0],
    ]);
    renderThemed(<HBarChart data={data} measure={dollars("Stolen value")} />);
    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Stolen value" })).toBeInTheDocument();
    expect(within(table).getByText("$14,479,512,996")).toBeInTheDocument();
    expect(within(table).getByText("Livestock")).toBeInTheDocument(); // the zero row stays
    expect(within(table).getByText("$0.00")).toBeInTheDocument();
    expect(screen.queryByText(/Arrests/)).not.toBeInTheDocument();
  });

  it("says when the chart shows only the top categories (LESDC fixture)", () => {
    const data = rows(
      [
        ["Firearm", 36],
        ["Hanging", 3],
        ["Jumping", 1],
        ["Asphyxiation", 1],
        ["Suffocation", 1],
        ["Drowning", 1],
        ["Poisoning", 1],
        ["Other", 0],
        ["Unknown", null],
      ],
      "manner",
    );
    renderThemed(<HBarChart data={data} measure={count("Suicides")} />);
    expect(screen.getByText(/Top 6 of 9 categories · Suicides/)).toBeInTheDocument();
    const cells = within(screen.getByRole("table")).getAllByRole("row");
    expect(cells).toHaveLength(10); // header + all 9 categories
    expect(within(screen.getByRole("table")).getByText("—")).toBeInTheDocument(); // null value
  });
});
