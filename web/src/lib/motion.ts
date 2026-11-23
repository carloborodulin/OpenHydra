/**
 * False when the user asks the system for reduced motion. Recharts and MapLibre
 * animate in JavaScript, which the CSS media query cannot stop, so they read
 * this value. It is read once at load; the setting rarely changes in a session.
 */
export const ANIMATE: boolean = !(
  typeof window !== "undefined" &&
  typeof window.matchMedia === "function" &&
  window.matchMedia("(prefers-reduced-motion: reduce)").matches
);
