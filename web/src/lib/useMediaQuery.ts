import { useEffect, useState } from "react";

// matchMedia-based responsive hook. Guards window access so it degrades safely
// in non-browser environments, and seeds from the current match. Recharts axis
// `width` / tick `fontSize` are SVG layout props that CSS can't reach, so charts
// read this to shrink their axes on small screens.
export function useMediaQuery(query: string): boolean {
  const get = () =>
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia(query).matches
      : false;
  const [matches, setMatches] = useState(get);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange(); // resync between initial render and effect
    mql.addEventListener("change", onChange);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

// Below Tailwind's `lg` (1024px). 1023.98 keeps the JS flip aligned with the CSS
// `lg:` breakpoint, so the desktop layout (>= 1024px) stays untouched.
export const useIsMobile = () => useMediaQuery("(max-width: 1023.98px)");
