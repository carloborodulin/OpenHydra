// Shared "HUD" button styling. Centralizing it keeps the cyan active/inactive
// treatment from drifting across the nav tabs, the mobile nav drawer, and the
// per-view offense/year/geo pickers.

// Active vs. inactive color treatment, shared by every HUD button.
export function hudState(active: boolean): string {
  return active
    ? "glow border-accent bg-accent/10 text-accent"
    : "border-line text-muted hover:border-line-strong hover:text-ink";
}

// Full styling for a per-view picker / toggle button. Gives a 48px touch target
// on mobile, restored to the dense desktop sizing at lg (matching the original
// `px-2.5 py-1 text-[0.62rem]`). Append extra utilities (e.g. disabled styles)
// at the call site.
export function hudBtn(active: boolean): string {
  return `mono inline-flex min-h-12 shrink-0 cursor-pointer items-center border px-3 py-2.5 text-[0.68rem] tracking-wider uppercase transition lg:min-h-0 lg:px-2.5 lg:py-1 lg:text-[0.62rem] ${hudState(active)}`;
}
