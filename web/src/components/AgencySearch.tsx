import { useId, useMemo, useState } from "react";
import type { AgencyFeature } from "../lib/api";
import { MAX_RESULTS, searchAgencies } from "../lib/agencySearch";

// A keyboard and screen-reader path to the agency drill-down, next to the map.
// WAI-ARIA "combobox with list autocomplete": focus stays in the text box,
// Down/Up move through the results, Enter opens the agency, Escape clears.
export function AgencySearch({
  agencies,
  onSelect,
}: {
  agencies: AgencyFeature[];
  onSelect: (ori: string, name: string) => void;
}) {
  const id = useId();
  const listId = `${id}-results`;
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [open, setOpen] = useState(false);
  const results = useMemo(() => searchAgencies(agencies, query), [agencies, query]);
  const showList = open && results.length > 0;

  const pick = (a: AgencyFeature) => {
    onSelect(a.ori, a.agency_name ?? a.ori);
    setQuery("");
    setOpen(false);
  };

  return (
    <div className="relative">
      <label htmlFor={`${id}-input`} className="sr-only">
        Find an agency by name, ORI or county
      </label>
      <input
        id={`${id}-input`}
        type="search"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={showList}
        aria-controls={listId}
        aria-activedescendant={showList ? `${id}-r-${active}` : undefined}
        autoComplete="off"
        placeholder="Find an agency…"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setActive(0);
          setOpen(true);
        }}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setOpen(true);
            setActive((i) => Math.min(results.length - 1, i + 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((i) => Math.max(0, i - 1));
          } else if (e.key === "Enter" && showList) {
            e.preventDefault();
            pick(results[active]);
          } else if (e.key === "Escape") {
            if (showList) setOpen(false);
            else setQuery("");
          }
        }}
        className="mono w-full border-b border-line-strong bg-bg2 px-3 py-2 text-[0.7rem] text-ink placeholder:text-muted"
      />
      <span className="sr-only" aria-live="polite">
        {open && query
          ? `${results.length}${results.length === MAX_RESULTS ? " or more" : ""} agencies found`
          : ""}
      </span>
      {showList && (
        <ul
          id={listId}
          role="listbox"
          aria-label="Agencies"
          className="absolute inset-x-0 top-full z-10 max-h-64 overflow-y-auto border border-line-strong bg-bg2 shadow-lg"
        >
          {results.map((a, i) => (
            <li
              key={a.ori}
              id={`${id}-r-${i}`}
              role="option"
              aria-selected={i === active}
              // mousedown, not click: it fires before the input blur closes the list.
              onMouseDown={(e) => {
                e.preventDefault();
                pick(a);
              }}
              onMouseMove={() => setActive(i)}
              className={`mono cursor-pointer px-3 py-1.5 text-[0.68rem] ${
                i === active ? "bg-accent/15 text-accent" : "text-ink"
              }`}
            >
              {a.agency_name ?? a.ori}
              <span className="text-muted">
                {" "}
                · {a.ori}
                {a.county ? ` · ${a.county}` : ""}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
