import { regionName } from "../lib/states";
import { titleCase } from "../lib/format";
import { Select } from "./Select";

interface Props {
  offenses: string[];
  value: string;
  onChange: (offense: string) => void;
  states: string[];
  region: string;
  onRegionChange: (region: string) => void;
  // The offense button-group applies only to summarized-offense views (Overview);
  // hide it on views that use their own dimensions (e.g. Hate Crime).
  showOffenses?: boolean;
}

export function Controls({
  offenses,
  value,
  onChange,
  states,
  region,
  onRegionChange,
  showOffenses = true,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-2">
        <span className="panel-title shrink-0">Region</span>
        <Select
          value={region}
          onChange={onRegionChange}
          options={[
            { value: "US", label: regionName("US") },
            ...states.map((s) => ({ value: s, label: regionName(s) })),
          ]}
          title="Region"
          className="w-44"
        />
      </div>

      {showOffenses && (
        <>
          <span className="h-4 w-px bg-line" />
          <div className="flex flex-wrap items-center gap-1.5">
            {offenses.map((o) => {
              const active = o === value;
              return (
                <button
                  key={o}
                  type="button"
                  onClick={() => onChange(o)}
                  className={`mono cursor-pointer border px-2.5 py-1 text-[0.62rem] tracking-wider uppercase transition ${
                    active
                      ? "glow border-accent bg-[rgba(34,211,238,0.1)] text-accent"
                      : "border-line text-muted hover:border-line-strong hover:text-ink"
                  }`}
                >
                  {titleCase(o)}
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
