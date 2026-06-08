import { titleCase } from "../lib/format";

interface Props {
  offenses: string[];
  value: string;
  onChange: (offense: string) => void;
}

export function Controls({ offenses, value, onChange }: Props) {
  return (
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
  );
}
