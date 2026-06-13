import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export interface SelectOption {
  value: string;
  label: string;
}
export interface SelectGroup {
  label: string;
  options: SelectOption[];
}

interface Props {
  value: string;
  onChange: (value: string) => void;
  options?: SelectOption[]; // ungrouped, rendered first
  groups?: SelectGroup[]; // grouped, rendered after, with a header per group
  title?: string;
  className?: string; // trigger width, e.g. "w-44"
  placeholder?: string;
}

// Themed dropdown matching the command-center HUD — replaces native <select>,
// which can't be styled past the closed box. The popup is portaled to <body>
// with fixed positioning so the panels' backdrop-filter stacking contexts (and
// any overflow:auto scroll containers) can't clip or paint over it. Closes on
// outside click, Escape, or scroll/resize (which would detach the fixed popup).
export function Select({
  value,
  onChange,
  options = [],
  groups = [],
  title,
  className = "",
  placeholder,
}: Props) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{
    top: number;
    left: number;
    minWidth: number;
    maxWidth: number;
  } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  const all = [...options, ...groups.flatMap((g) => g.options)];
  const current = all.find((o) => o.value === value);

  useLayoutEffect(() => {
    if (!open) return;
    const r = triggerRef.current?.getBoundingClientRect();
    if (!r) return;
    // Clamp the portaled popup to the viewport so it can't run off the right edge
    // on narrow screens. On desktop vw is large, so maxWidth resolves to the 22rem
    // cap and left stays r.left — i.e. the positioning is unchanged there.
    const gutter = 8;
    const vw = window.innerWidth;
    const maxWidth = Math.min(352, vw - gutter * 2); // 352 = 22rem
    const left = Math.max(gutter, Math.min(r.left, vw - maxWidth - gutter));
    setPos({ top: r.bottom + 5, left, minWidth: Math.min(r.width, maxWidth), maxWidth });
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t) || popupRef.current?.contains(t)) return;
      setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const close = () => setOpen(false);
    // Close when the page scrolls, but ignore scrolls inside the popup's own list
    // (otherwise dragging a long list on mobile dismisses it mid-scroll).
    const onScroll = (e: Event) => {
      if (popupRef.current?.contains(e.target as Node)) return;
      setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", close);
    window.addEventListener("scroll", onScroll, true); // capture → catches nested scrollers
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [open]);

  const pick = (v: string) => {
    onChange(v);
    setOpen(false);
  };

  return (
    <div className={`relative ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        title={title}
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="mono flex min-h-12 w-full items-center justify-between gap-2 border border-line bg-accent/[0.06] px-2.5 py-2.5 text-left text-[0.68rem] tracking-wider text-accent uppercase transition hover:border-line-strong focus:border-accent focus:outline-none lg:min-h-0 lg:py-1 lg:text-[0.62rem]"
      >
        <span className="truncate">{current?.label ?? placeholder ?? value}</span>
        <span
          aria-hidden
          className={`shrink-0 text-[0.55rem] transition-transform duration-150 ${
            open ? "rotate-180 text-accent" : "text-muted"
          }`}
        >
          ▾
        </span>
      </button>

      {open &&
        pos &&
        createPortal(
          <div
            ref={popupRef}
            role="listbox"
            style={{ top: pos.top, left: pos.left, minWidth: pos.minWidth, maxWidth: pos.maxWidth }}
            className="fixed z-[100] max-h-[60vh] w-max max-w-[22rem] overflow-y-auto border border-line-strong bg-bg2 py-1 shadow-[0_10px_30px_rgba(0,0,0,0.3)]"
          >
            {options.map((o) => (
              <Item key={o.value} option={o} active={o.value === value} onPick={pick} />
            ))}
            {groups.map((g) => (
              <div key={g.label}>
                <div className="mono px-2.5 pt-2 pb-1 text-[0.5rem] tracking-[0.2em] text-muted uppercase">
                  {g.label}
                </div>
                {g.options.map((o) => (
                  <Item key={o.value} option={o} active={o.value === value} onPick={pick} />
                ))}
              </div>
            ))}
          </div>,
          document.body,
        )}
    </div>
  );
}

function Item({
  option,
  active,
  onPick,
}: {
  option: SelectOption;
  active: boolean;
  onPick: (v: string) => void;
}) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={active}
      onClick={() => onPick(option.value)}
      className={`mono flex min-h-12 w-full cursor-pointer items-center px-3 text-left text-[0.7rem] tracking-wider uppercase transition lg:min-h-0 lg:px-2.5 lg:py-1 lg:text-[0.62rem] ${
        active
          ? "glow bg-accent/15 text-accent"
          : "text-muted hover:bg-accent/[0.07] hover:text-ink"
      }`}
    >
      <span className="truncate">{option.label}</span>
    </button>
  );
}
