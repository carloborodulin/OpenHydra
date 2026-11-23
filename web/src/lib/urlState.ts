import { useCallback, useEffect, useState } from "react";

/**
 * The dashboard state that a link can share. It lives in the query string, for
 * example `?view=overview&region=NY&offense=homicide&agency=NY0303000`, so a
 * reload keeps it and the browser's back and forward buttons move through it.
 */
export interface UrlState {
  view: string;
  region: string; // "US" = national
  offense: string;
  agency: string | null; // ORI of the drilled-in agency
  compare: string | null; // a second state for the comparison overlay
}

export const DEFAULTS: UrlState = {
  view: "overview",
  region: "US",
  offense: "homicide",
  agency: null,
  compare: null,
};

const ORI = /^[A-Z]{2}[A-Z0-9]{7}$/;
const AREA = /^[A-Z]{2}$/;
const SLUG = /^[a-z-]{1,40}$/;

/** Read the state from a query string. Malformed values fall back to defaults. */
export function parseState(search: string): UrlState {
  const q = new URLSearchParams(search);
  const get = (k: string) => q.get(k)?.trim() ?? "";
  const region = get("region").toUpperCase();
  const agency = get("agency").toUpperCase();
  const compare = get("compare").toUpperCase();
  return {
    view: SLUG.test(get("view")) ? get("view") : DEFAULTS.view,
    region: AREA.test(region) ? region : DEFAULTS.region,
    offense: SLUG.test(get("offense")) ? get("offense") : DEFAULTS.offense,
    agency: ORI.test(agency) ? agency : null,
    compare: AREA.test(compare) && compare !== "US" ? compare : null,
  };
}

/** Write the state as a query string, leaving out the defaults. */
export function serializeState(s: UrlState): string {
  const q = new URLSearchParams();
  (Object.keys(DEFAULTS) as (keyof UrlState)[]).forEach((k) => {
    const v = s[k];
    if (v != null && v !== DEFAULTS[k]) q.set(k, v);
  });
  const text = q.toString();
  return text ? `?${text}` : "";
}

/**
 * The next state after a change. A new region or view leaves the agency and
 * the comparison behind, because they belong to the old scope (BUG-3).
 */
export function nextState(prev: UrlState, patch: Partial<UrlState>): UrlState {
  const next = { ...prev, ...patch };
  if (patch.region !== undefined && patch.region !== prev.region) {
    if (!("agency" in patch)) next.agency = null;
    if (next.compare === next.region) next.compare = null;
  }
  return next;
}

export function useUrlState(): [UrlState, (patch: Partial<UrlState>) => void] {
  const [state, setState] = useState(() => parseState(window.location.search));

  useEffect(() => {
    const onPop = () => setState(parseState(window.location.search));
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const update = useCallback((patch: Partial<UrlState>) => {
    setState((prev) => {
      const next = nextState(prev, patch);
      const search = serializeState(next);
      if (search !== window.location.search) {
        window.history.pushState(null, "", `${window.location.pathname}${search}`);
      }
      return next;
    });
  }, []);

  return [state, update];
}
