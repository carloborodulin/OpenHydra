import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from "react";
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
  /** The accessible name, for example "Region". Also the tooltip. */
  title?: string;
  className?: string; // trigger width, e.g. "w-44"
  placeholder?: string;
}

// Themed dropdown that follows the WAI-ARIA "select-only combobox" pattern:
// https://www.w3.org/WAI/ARIA/apg/patterns/combobox/examples/combobox-select-only/
//
// Focus stays on the trigger. aria-activedescendant points at the active option.
// Keys: Down/Up/Home/End/PageDown/PageUp move, Enter/Space choose, Escape closes,
// Tab chooses and moves on, and typing jumps to the first label that matches.
//
// The popup is portaled to <body> with fixed positioning so the panels'
// backdrop-filter stacking contexts (and any overflow:auto scroll containers)
// can't clip or paint over it. It closes on outside click, Escape, or a page
// scroll or resize (which would detach the fixed popup).
export function Select({
  value,
  onChange,
  options = [],
  groups = [],
  title,
  className = "",
  placeholder,
}: Props) {
  const id = useId();
  const listId = `${id}-list`;
  const optionId = (i: number) => `${id}-opt-${i}`;
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [pos, setPos] = useState<{
    top: number;
    left: number;
    minWidth: number;
    maxWidth: number;
  } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);
  const typed = useRef({ text: "", at: 0 });

  const all = useMemo(() => [...options, ...groups.flatMap((g) => g.options)], [options, groups]);
  const selectedIndex = Math.max(
    0,
    all.findIndex((o) => o.value === value),
  );
  const current = all.find((o) => o.value === value);

  const openList = (index = selectedIndex) => {
    setActive(index);
    setOpen(true);
  };
  const choose = (index: number) => {
    const o = all[index];
    if (o) onChange(o.value);
    setOpen(false);
  };

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
    setPos({
      top: r.bottom + 5,
      left,
      minWidth: Math.min(r.width, maxWidth),
      maxWidth,
    });
  }, [open]);

  // Keep the active option in view while the keyboard moves it.
  useEffect(() => {
    if (!open) return;
    document.getElementById(optionId(active))?.scrollIntoView?.({ block: "nearest" });
    // optionId is stable for one component instance.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, active, pos]);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      const t = e.target as Node;
      if (triggerRef.current?.contains(t) || popupRef.current?.contains(t)) return;
      setOpen(false);
    };
    const close = () => setOpen(false);
    // Close when the page scrolls, but ignore scrolls inside the popup's own list
    // (otherwise dragging a long list on mobile dismisses it mid-scroll).
    const onScroll = (e: Event) => {
      if (popupRef.current?.contains(e.target as Node)) return;
      setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    window.addEventListener("resize", close);
    window.addEventListener("scroll", onScroll, true); // capture → catches nested scrollers
    return () => {
      document.removeEventListener("pointerdown", onDown);
      window.removeEventListener("resize", close);
      window.removeEventListener("scroll", onScroll, true);
    };
  }, [open]);

  // Type to jump: a single key cycles through the labels that start with it; a
  // quick run of keys (within 600 ms) matches the whole prefix.
  const typeahead = (key: string) => {
    const now = Date.now();
    const t = typed.current;
    t.text = now - t.at > 600 ? key : t.text + key;
    t.at = now;
    const q = t.text.toLowerCase();
    const start = open ? active : selectedIndex;
    const offset = t.text.length === 1 ? 1 : 0;
    for (let k = 0; k < all.length; k++) {
      const i = (start + offset + k) % all.length;
      if (all[i].label.toLowerCase().startsWith(q)) return i;
    }
    return -1;
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>) => {
    const last = all.length - 1;
    if (!open) {
      if (["ArrowDown", "ArrowUp", "Enter", " "].includes(e.key)) {
        e.preventDefault();
        openList(e.key === "ArrowUp" ? Math.max(0, selectedIndex - 1) : selectedIndex);
      } else if (e.key === "Home" || e.key === "End") {
        e.preventDefault();
        openList(e.key === "Home" ? 0 : last);
      } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        const i = typeahead(e.key);
        if (i >= 0) openList(i);
      }
      return;
    }
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setActive((i) => Math.min(last, i + 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        if (e.altKey) choose(active);
        else setActive((i) => Math.max(0, i - 1));
        break;
      case "Home":
        e.preventDefault();
        setActive(0);
        break;
      case "End":
        e.preventDefault();
        setActive(last);
        break;
      case "PageDown":
        e.preventDefault();
        setActive((i) => Math.min(last, i + 10));
        break;
      case "PageUp":
        e.preventDefault();
        setActive((i) => Math.max(0, i - 10));
        break;
      case "Enter":
      case " ":
        e.preventDefault();
        choose(active);
        break;
      case "Escape":
        e.preventDefault();
        setOpen(false);
        break;
      case "Tab":
        choose(active); // no preventDefault: focus moves on as usual
        break;
      default:
        if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
          const i = typeahead(e.key);
          if (i >= 0) setActive(i);
        }
    }
  };

  // The flat index of each option across the ungrouped and grouped options.
  const indexOf = new Map(all.map((o, i) => [o.value, i]));
  const renderOption = (o: SelectOption) => {
    const i = indexOf.get(o.value) ?? 0;
    return (
      <Item
        key={o.value}
        id={optionId(i)}
        option={o}
        selected={o.value === value}
        active={open && i === active}
        onPick={() => {
          choose(i);
          triggerRef.current?.focus();
        }}
        onHover={() => setActive(i)}
      />
    );
  };

  return (
    <div className={`relative ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        role="combobox"
        title={title}
        // The name holds the visible value too (WCAG 2.5.3, label in name).
        aria-label={title ? `${title}: ${current?.label ?? placeholder ?? value}` : undefined}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-activedescendant={open ? optionId(active) : undefined}
        onClick={() => (open ? setOpen(false) : openList())}
        onKeyDown={onKeyDown}
        className="mono flex min-h-12 w-full items-center justify-between gap-2 border border-line-strong bg-accent/[0.06] px-2.5 py-2.5 text-left text-[0.68rem] tracking-wider text-accent uppercase transition hover:border-accent lg:min-h-0 lg:py-1 lg:text-[0.62rem]"
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
            id={listId}
            role="listbox"
            aria-label={title}
            style={{
              top: pos.top,
              left: pos.left,
              minWidth: pos.minWidth,
              maxWidth: pos.maxWidth,
            }}
            className="fixed z-[100] max-h-[60vh] w-max max-w-[22rem] overflow-y-auto border border-line-strong bg-bg2 py-1 shadow-[0_10px_30px_rgba(0,0,0,0.3)]"
          >
            {options.map(renderOption)}
            {groups.map((g, gi) => (
              <div key={g.label} role="group" aria-labelledby={`${id}-group-${gi}`}>
                <div
                  id={`${id}-group-${gi}`}
                  role="presentation"
                  className="mono px-2.5 pt-2 pb-1 text-[0.5rem] tracking-[0.2em] text-muted uppercase"
                >
                  {g.label}
                </div>
                {g.options.map(renderOption)}
              </div>
            ))}
          </div>,
          document.body,
        )}
    </div>
  );
}

function Item({
  id,
  option,
  selected,
  active,
  onPick,
  onHover,
}: {
  id: string;
  option: SelectOption;
  selected: boolean;
  active: boolean;
  onPick: () => void;
  onHover: () => void;
}) {
  return (
    <div
      id={id}
      role="option"
      aria-selected={selected}
      onClick={onPick}
      onPointerMove={onHover}
      className={`mono flex min-h-12 w-full cursor-pointer items-center px-3 text-left text-[0.7rem] tracking-wider uppercase transition lg:min-h-0 lg:px-2.5 lg:py-1 lg:text-[0.62rem] ${
        selected ? "glow bg-accent/15 text-accent" : "text-muted hover:text-ink"
      } ${active ? "outline outline-2 -outline-offset-2 outline-accent" : ""}`}
    >
      <span className="truncate">{option.label}</span>
    </div>
  );
}
