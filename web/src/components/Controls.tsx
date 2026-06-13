import { regionName } from "../lib/states";
import { titleCase } from "../lib/format";
import { hudBtn } from "../lib/ui";
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
    <div className="flex flex-col items-stretch gap-3 lg:flex-row lg:flex-wrap lg:items-center lg:gap-4">
      <div className="flex w-full items-center gap-2 lg:w-auto">
        <span className="panel-title shrink-0">Region</span>
        <Select
          value={region}
          onChange={onRegionChange}
          options={[
            { value: "US", label: regionName("US") },
            ...states.map((s) => ({ value: s, label: regionName(s) })),
          ]}
          title="Region"
          className="w-full lg:w-44"
        />
      </div>

      {showOffenses && (
        <>
          <span className="hidden h-4 w-px bg-line lg:block" />
          <div className="flex flex-wrap items-center gap-1.5">
            {offenses.map((o) => (
              <button
                key={o}
                type="button"
                onClick={() => onChange(o)}
                className={hudBtn(o === value)}
              >
                {titleCase(o)}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
