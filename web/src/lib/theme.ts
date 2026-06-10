import { createContext, useContext, useMemo } from "react";

// Two distinct looks: the default neon "command-center / HUD" (dark) and a
// light "analytics platform" (GA-style) theme. The active theme is driven by a
// `data-theme` attribute on <html>; every color is a CSS variable in index.css,
// so most of the UI re-themes for free. Charts are the exception — see
// useChartColors below. The <ThemeProvider> lives in ./ThemeProvider (kept in a
// separate file so this hook/context module stays Fast-Refresh friendly).
export type Theme = "dark" | "light";

export const STORAGE_KEY = "oh-theme";

export interface ThemeCtx {
  theme: Theme;
  toggle: () => void;
  setTheme: (t: Theme) => void;
}

export const ThemeContext = createContext<ThemeCtx | null>(null);

export function readStoredTheme(): Theme {
  const fromDom = document.documentElement.dataset.theme;
  if (fromDom === "light" || fromDom === "dark") return fromDom;
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark") return v;
  } catch {
    /* localStorage may be unavailable (private mode) — fall through */
  }
  return "dark"; // dark HUD is the default first impression
}

// Apply the theme to the DOM + storage synchronously, BEFORE React re-renders,
// so consumers that read resolved CSS variables (useChartColors) see fresh
// values on the very next render instead of one frame behind.
export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    /* ignore write failures */
  }
}

export function useTheme(): ThemeCtx {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within <ThemeProvider>");
  return ctx;
}

// Recharts renders colors as SVG *presentation attributes*, which do NOT resolve
// `var(--x)`. So we read the resolved CSS-variable values in JS (re-running on
// every theme change) and hand charts concrete color strings.
const VARS = {
  accent: "--color-accent",
  good: "--color-good",
  warn: "--color-warn",
  alert: "--color-alert",
  violet: "--color-violet",
  muted: "--color-muted",
  ink: "--color-ink",
  bg: "--color-bg",
  grid: "--color-grid",
  axis: "--color-axis",
  font: "--font-mono",
} as const;

export interface ChartColors {
  accent: string;
  good: string;
  warn: string;
  alert: string;
  violet: string;
  muted: string;
  ink: string;
  bg: string;
  grid: string;
  axis: string;
  font: string;
  palette: string[];
}

export function useChartColors(): ChartColors {
  const { theme } = useTheme();
  return useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    const read = (v: string) => cs.getPropertyValue(v).trim();
    const c = Object.fromEntries(
      Object.entries(VARS).map(([k, v]) => [k, read(v)]),
    ) as Omit<ChartColors, "palette">;
    return { ...c, palette: [c.accent, c.good, c.violet, c.warn, c.alert, c.muted] };
    // theme is the cache key: when it flips, the data-theme attribute has already
    // been applied synchronously, so getComputedStyle reads the new variable set.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);
}
