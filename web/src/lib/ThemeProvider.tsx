import { useMemo, useState, type ReactNode } from "react";
import { applyTheme, readStoredTheme, ThemeContext, type Theme, type ThemeCtx } from "./theme";

// Holds the active theme and exposes it via context. Kept separate from the
// hooks in ./theme so that module can be a pure (component-free) Fast-Refresh
// boundary. The initial value comes from the data-theme attribute that the
// inline boot script in index.html sets before first paint (no flash).
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(readStoredTheme);

  const value = useMemo<ThemeCtx>(() => {
    const setTheme = (t: Theme) => {
      applyTheme(t);
      setThemeState(t);
    };
    return {
      theme,
      setTheme,
      toggle: () => setTheme(theme === "dark" ? "light" : "dark"),
    };
  }, [theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
