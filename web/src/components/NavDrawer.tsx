import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { hudState } from "../lib/ui";
import type { NavItem } from "./Nav";

export const NAV_DRAWER_ID = "nav-drawer";

interface Props {
  items: NavItem[];
  active: string;
  open: boolean;
  onClose: () => void;
  onSelect: (id: string) => void;
}

const FOCUSABLE = 'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])';

// Mobile-only (< lg) view switcher: a modal dialog that slides in from the left.
// - While closed, the whole drawer is `inert`, so no control in it can take
//   focus or reach a screen reader.
// - On open, focus moves to the close button and Tab cycles inside the drawer.
// - On close, focus goes back to the control that opened it (the menu button).
// - Escape, the backdrop, the close button and a resize to the desktop layout
//   all close it.
export function NavDrawer({ items, active, open, onClose, onSelect }: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  // App passes a new onClose each render; the effect reads the latest one.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!open) return;
    const opener = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab" || !panelRef.current) return;
      const nodes = [...panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (!nodes.length) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // The drawer exists only below lg; close it if the layout becomes desktop.
    const desktop = window.matchMedia?.("(min-width: 1024px)");
    const onBreakpoint = (e: MediaQueryListEvent) => e.matches && onCloseRef.current();
    desktop?.addEventListener("change", onBreakpoint);

    return () => {
      document.removeEventListener("keydown", onKey);
      desktop?.removeEventListener("change", onBreakpoint);
      document.body.style.overflow = prevOverflow;
      opener?.focus?.();
    };
  }, [open]);

  return createPortal(
    <div
      className={`fixed inset-0 z-[200] lg:hidden ${open ? "" : "pointer-events-none"}`}
      inert={!open}
    >
      {/* Backdrop (pointer only; the close button is the keyboard path). */}
      <div
        aria-hidden
        onClick={onClose}
        className={`absolute inset-0 bg-black/60 transition-opacity duration-200 motion-reduce:transition-none ${
          open ? "opacity-100" : "opacity-0"
        }`}
      />
      <div
        ref={panelRef}
        id={NAV_DRAWER_ID}
        role="dialog"
        aria-modal="true"
        aria-label="Views"
        className={`panel brackets absolute inset-y-0 left-0 flex w-72 max-w-[80vw] flex-col gap-1.5 overflow-y-auto p-3 transition-transform duration-200 motion-reduce:transition-none ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-1 flex items-center justify-between px-1">
          <span className="panel-title">Views</span>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="flex h-12 w-12 cursor-pointer items-center justify-center border border-line text-accent hover:border-line-strong"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              aria-hidden
            >
              <path d="M6 6l12 12M18 6L6 18" />
            </svg>
          </button>
        </div>
        <nav aria-label="Views">
          <ul className="flex flex-col gap-1.5">
            {items.map((it) => (
              <li key={it.id}>
                <button
                  type="button"
                  aria-current={it.id === active ? "page" : undefined}
                  onClick={() => onSelect(it.id)}
                  className={`mono flex min-h-12 w-full cursor-pointer items-center border px-3 text-[0.7rem] tracking-wider uppercase transition ${hudState(
                    it.id === active,
                  )}`}
                >
                  {it.label}
                </button>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </div>,
    document.body,
  );
}
