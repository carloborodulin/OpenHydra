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
  const [pos, setPos] = useState<{ top: number; left: number; minWidth: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  const all = [...options, ...groups.flatMap((g) => g.options)];
  const current = all.find((o) => o.value === value);

  useLayoutEffect(() => {
    if (!open) return;
    const r = triggerRef.current?.getBoundingClientRect();
    if (r) setPos({ top: r.bottom + 5, left: r.left, minWidth: r.width });
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
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", close);
    window.addEventListener("scroll", close, true); // capture → catches nested scrollers
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", close, true);
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
        className="mono flex w-full items-center justify-between gap-2 border border-line bg-accent/[0.06] px-2.5 py-1 text-left text-[0.62rem] tracking-wider text-accent uppercase transition hover:border-line-strong focus:border-accent focus:outline-none"
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
            style={{ top: pos.top, left: pos.left, minWidth: pos.minWidth }}
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
      className={`mono block w-full cursor-pointer truncate px-2.5 py-1 text-left text-[0.62rem] tracking-wider uppercase transition ${
        active
          ? "glow bg-accent/15 text-accent"
          : "text-muted hover:bg-accent/[0.07] hover:text-ink"
      }`}
    >
      {option.label}
    </button>
  );
}
