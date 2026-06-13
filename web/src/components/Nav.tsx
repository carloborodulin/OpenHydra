import { hudState } from "../lib/ui";

export interface NavItem {
  id: string;
  label: string;
}

interface Props {
  items: NavItem[];
  active: string;
  onSelect: (id: string) => void;
}

// Desktop (>= lg) top-level view switcher. Below lg this is hidden and replaced
// by the TopBar hamburger + NavDrawer. New domain views (Hate Crime, Homicide,
// …) register by adding an entry to the items list in App.tsx.
export function Nav({ items, active, onSelect }: Props) {
  return (
    <nav className="hidden flex-wrap items-center gap-1.5 lg:flex">
      {items.map((it) => (
        <button
          key={it.id}
          type="button"
          onClick={() => onSelect(it.id)}
          className={`mono cursor-pointer border px-3 py-1 text-[0.62rem] tracking-wider uppercase transition ${hudState(
            it.id === active,
          )}`}
        >
          {it.label}
        </button>
      ))}
    </nav>
  );
}
