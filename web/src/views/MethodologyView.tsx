import { useEffect } from "react";
import { useRelease } from "../lib/release";
import { fmtDay, fmtWindow } from "../lib/snapshot";

interface Term {
  id: string;
  term: string;
  text: string[];
}

// Definitions for each measure on the dashboard. Each StatTile and panel that
// shows one of these links here with ?view=methodology#<id>.
const TERMS: Term[] = [
  {
    id: "offenses",
    term: "Offenses (rate per 100,000)",
    text: [
      "Offenses known to law enforcement, from the FBI Uniform Crime Reporting (UCR) program, as the CDE API publishes them. The rate is offenses per 100,000 residents of the area, computed by the FBI.",
      "Violent crime and property crime are FBI totals of their Part I offenses.",
    ],
  },
  {
    id: "ttm",
    term: "Trailing 12 months (TTM) and the 2019 index",
    text: [
      "The TTM rate of a month is the mean monthly rate of the 12 calendar months that end with it. It is empty unless all 12 months have a rate, so the first 11 months of the series and any gap stay empty.",
      "The 2019 index is the TTM rate divided by the mean monthly rate of calendar 2019, times 100. December 2019 is 100. The year-on-year change compares the TTM rate with the TTM rate 12 months earlier.",
    ],
  },
  {
    id: "clearance",
    term: "Clearances and the clearance rate",
    text: [
      "An offense is cleared by arrest, or by exceptional means when the police identify the offender but cannot arrest (for example, the offender died). The FBI counts a clearance in the month it happens, which can be later than the month of the offense.",
      "A monthly clearance ratio is cleared ÷ reported for that month. An annual clearance rate is cleared ÷ reported, both summed over the months of the year that report both counts. It is not the share of that year's offenses that were solved. A year with fewer than 12 such months is marked partial.",
    ],
  },
  {
    id: "arrests",
    term: "Arrests",
    text: [
      "Arrest totals over the extract window, by arrestee race, sex and age, for one arrest offense code. The code 'all' is every offense together. Each arrest counts under one offense.",
      "Violent crime and property crime have no arrest code. The dashboard shows them as the sum of their four Part I offenses (homicide, rape, robbery, aggravated assault; burglary, larceny, motor vehicle theft, arson) and marks them as derived.",
    ],
  },
  {
    id: "agencies",
    term: "Reporting agencies, NIBRS and SRS",
    text: [
      "An agency is a law enforcement unit with an ORI identifier. NIBRS agencies report incident-based data; SRS agencies report only the older Summary Reporting System counts. The map and the NIBRS adoption chart use the year each agency started NIBRS, from today's agency list. They do not show which agencies submitted data in a given year.",
    ],
  },
  {
    id: "staffing",
    term: "Police employment",
    text: [
      "Law enforcement employees from the FBI police employment collection: sworn officers and civilian staff. The staffing rate is employees per 1,000 residents, as the FBI publishes it. It counts all employees, not only sworn officers.",
    ],
  },
  {
    id: "uof",
    term: "Use-of-force participation",
    text: [
      "The FBI participation figure is the share of sworn officers that the participating agencies employ. The agency share is participating agencies ÷ all agencies. The two use different denominators, so they differ (2022: 75% and 55.9%). A dash means the FBI reports no value.",
    ],
  },
  {
    id: "property",
    term: "Expanded property values",
    text: [
      "Stolen and recovered property values from the FBI supplemental data. With yearly data, the per-resident value is the year's dollars ÷ the Census population of the same year. An older snapshot has only totals for the whole window; the dashboard then says so.",
    ],
  },
  {
    id: "estimates",
    term: "NIBRS estimates and their intervals",
    text: [
      "The FBI estimates national and regional NIBRS figures from the agencies that report. Each estimate has an interval (a lower and an upper bound) from the FBI. A difference between two estimates whose intervals overlap may not be real.",
    ],
  },
  {
    id: "snapshot",
    term: "The data snapshot and revisions",
    text: [
      "The warehouse views show a dated release of FBI data. The FBI revises past months, so the live CDE values can differ from this release. Each view footer gives the release, its window and the extraction date. A new release replaces a domain only when it covers at least as much as the last release; the release notes list the changed values.",
      "Agency drill-down calls the CDE API live. The 'Live' badge shows only after a successful live answer, with the dates it covers.",
    ],
  },
];

export function MethodologyView() {
  const s = useRelease();
  // A link such as ?view=methodology#clearance opens at that definition.
  useEffect(() => {
    const id = window.location.hash.slice(1);
    if (id) document.getElementById(id)?.scrollIntoView?.();
  }, []);
  return (
    // A scroll area must be reachable by keyboard (tabIndex) and named.
    <div
      className="mx-auto w-full max-w-3xl flex-1 overflow-auto p-3"
      tabIndex={0}
      role="region"
      aria-label="Methodology"
    >
      <article className="panel brackets enter flex flex-col gap-5 px-5 py-4 text-[0.82rem] leading-relaxed text-ink">
        <header>
          <h2 className="panel-title mb-2">Methodology and definitions</h2>
          {s && (
            <p className="text-muted">
              Release <span className="text-ink">{s.release_id}</span> · data{" "}
              {fmtWindow(s.window_from, s.window_to)} · extracted {fmtDay(s.extracted_at_max)}
              {s.reconstructed && " (dates from the project history)"}. Source: FBI Crime Data
              Explorer API.
            </p>
          )}
        </header>
        {TERMS.map((t) => (
          <section key={t.id} id={t.id} aria-labelledby={`${t.id}-h`} className="scroll-mt-4">
            <h3 id={`${t.id}-h`} className="mb-1 font-semibold">
              {t.term}
            </h3>
            {t.text.map((p, i) => (
              <p key={i} className="mb-1 text-muted">
                {p}
              </p>
            ))}
          </section>
        ))}
      </article>
    </div>
  );
}
