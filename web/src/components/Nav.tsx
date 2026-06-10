export interface NavItem {
  id: string;
  label: string;
}

interface Props {
  items: NavItem[];
  active: string;
  onSelect: (id: string) => void;
}

// Top-level view switcher. New domain views (Hate Crime, Homicide, …) register
// by adding an entry to the items list in App.tsx.
export function Nav({ items, active, onSelect }: Props) {
  return (
    <nav className="flex flex-wrap items-center gap-1.5">
      {items.map((it) => {
        const on = it.id === active;
        return (
          <button
            key={it.id}
            type="button"
            onClick={() => onSelect(it.id)}
            className={`mono cursor-pointer border px-3 py-1 text-[0.62rem] tracking-wider uppercase transition ${
              on
                ? "glow border-accent bg-[rgba(34,211,238,0.1)] text-accent"
                : "border-line text-muted hover:border-line-strong hover:text-ink"
            }`}
          >
            {it.label}
          </button>
        );
      })}
    </nav>
  );
}
