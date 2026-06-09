import { regionName } from "../lib/states";
import { titleCase } from "../lib/format";

interface Props {
  offenses: string[];
  value: string;
  onChange: (offense: string) => void;
  states: string[];
  region: string;
  onRegionChange: (region: string) => void;
}

export function Controls({ offenses, value, onChange, states, region, onRegionChange }: Props) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <div className="flex items-center gap-2">
        <span className="panel-title shrink-0">Region</span>
        <select
          value={region}
          onChange={(e) => onRegionChange(e.target.value)}
          className="mono cursor-pointer border border-line bg-[rgba(34,211,238,0.06)] px-2.5 py-1 text-[0.62rem] tracking-wider text-accent uppercase transition hover:border-line-strong focus:border-accent focus:outline-none"
        >
          <option value="US">{regionName("US")}</option>
          {states.map((s) => (
            <option key={s} value={s}>
              {regionName(s)}
            </option>
          ))}
        </select>
      </div>

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
    </div>
  );
}
