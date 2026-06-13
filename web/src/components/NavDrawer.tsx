import { useEffect } from "react";
import { createPortal } from "react-dom";
import { hudState } from "../lib/ui";
import type { NavItem } from "./Nav";

interface Props {
  items: NavItem[];
  active: string;
  open: boolean;
  onClose: () => void;
  onSelect: (id: string) => void;
}

// Mobile-only (< lg) slide-in view switcher. The desktop tab row (Nav) is hidden
// below lg and replaced by the TopBar hamburger, which opens this drawer. Always
// mounted (so it can animate); `lg:hidden` keeps it out of the desktop layout.
export function NavDrawer({ items, active, open, onClose, onSelect }: Props) {
  // Close on Escape and lock background scroll while the drawer is open.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  return createPortal(
    <div
      className={`fixed inset-0 z-[200] lg:hidden ${open ? "" : "pointer-events-none"}`}
      aria-hidden={!open}
    >
      {/* Backdrop */}
      <div
        onClick={onClose}
        className={`absolute inset-0 bg-black/60 transition-opacity duration-200 ${
          open ? "opacity-100" : "opacity-0"
        }`}
      />
      {/* Sliding panel */}
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Views"
        className={`panel brackets absolute inset-y-0 left-0 flex w-72 max-w-[80vw] flex-col gap-1.5 overflow-y-auto p-3 transition-transform duration-200 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <span className="panel-title mb-1 px-1">Views</span>
        {items.map((it) => (
          <button
            key={it.id}
            type="button"
            onClick={() => onSelect(it.id)}
            className={`mono flex min-h-12 cursor-pointer items-center border px-3 text-[0.7rem] tracking-wider uppercase transition ${hudState(
              it.id === active,
            )}`}
          >
            {it.label}
          </button>
        ))}
      </div>
    </div>,
    document.body,
  );
}
