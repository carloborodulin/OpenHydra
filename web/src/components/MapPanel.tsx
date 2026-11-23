import { Map as MapLibreMap, setWorkerUrl, type GeoJSONSource } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 is ESM-only and loads its worker from a separate module. Import the
// worker as an asset URL so Vite emits it with a content hash on our own origin.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?url";
import type { Feature, FeatureCollection } from "geojson";
import { useEffect, useRef, useState } from "react";
import type { AgencyFeature } from "../lib/api";
import { ANIMATE } from "../lib/motion";
import { useChartColors, useTheme, type ChartColors } from "../lib/theme";

setWorkerUrl(workerUrl);

const BASEMAP = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};

/** MapLibre 6 needs WebGL2. Old devices and some locked-down browsers lack it. */
function supportsWebGL2(): boolean {
  try {
    return Boolean(document.createElement("canvas").getContext("webgl2"));
  } catch {
    return false;
  }
}

// Sanity-bound to US lon/lat: drops mis-geocoded points (e.g. an agency at
// -9,-9) and the lone Aleutian outpost past the antimeridian that would
// otherwise stretch fitBounds across the whole globe.
const inUS = (lat: number, lon: number) => lon >= -180 && lon <= -64 && lat >= 15 && lat <= 72;

function toFeatures(agencies: AgencyFeature[]): Feature[] {
  const out: Feature[] = [];
  for (const a of agencies) {
    if (a.latitude == null || a.longitude == null || !inUS(a.latitude, a.longitude)) continue;
    out.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [a.longitude, a.latitude] },
      properties: {
        nibrs: a.is_nibrs ? 1 : 0,
        name: a.agency_name,
        ori: a.ori,
      },
    });
  }
  return out;
}

/** Bounding box with one pass (no spread of ~20k values into Math.min). */
function bounds(features: Feature[]): [[number, number], [number, number]] | null {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const f of features) {
    const [x, y] = (f.geometry as { coordinates: number[] }).coordinates;
    if (x < minX) minX = x;
    if (x > maxX) maxX = x;
    if (y < minY) minY = y;
    if (y > maxY) maxY = y;
  }
  return Number.isFinite(minX)
    ? [
        [minX, minY],
        [maxX, maxY],
      ]
    : null;
}

/** Add the agency source and layers, or update the data when they exist. */
function applyLayers(m: MapLibreMap, data: FeatureCollection, c: ChartColors) {
  const src = m.getSource("agencies") as GeoJSONSource | undefined;
  if (src) {
    src.setData(data);
    return;
  }
  m.addSource("agencies", { type: "geojson", data });
  m.addLayer({
    id: "agencies-glow",
    type: "circle",
    source: "agencies",
    paint: {
      "circle-radius": 16,
      "circle-blur": 1,
      "circle-opacity": 0.5,
      "circle-color": ["case", ["==", ["get", "nibrs"], 1], c.accent, c.warn],
    },
  });
  m.addLayer({
    id: "agencies-core",
    type: "circle",
    source: "agencies",
    // Blue vs orange stays distinct for common color vision deficiencies, and
    // the shape differs too: NIBRS is a filled dot, SRS a hollow ring.
    paint: {
      "circle-radius": ["case", ["==", ["get", "nibrs"], 1], 4, 3.5],
      "circle-color": ["case", ["==", ["get", "nibrs"], 1], c.accent, c.bg],
      "circle-stroke-color": ["case", ["==", ["get", "nibrs"], 1], c.bg, c.warn],
      "circle-stroke-width": ["case", ["==", ["get", "nibrs"], 1], 0.6, 2],
    },
  });
}

function fitTo(m: MapLibreMap, data: FeatureCollection) {
  const b = bounds(data.features);
  if (b) m.fitBounds(b, { padding: 48, duration: ANIMATE ? 900 : 0, maxZoom: 8 });
}

export function MapPanel({
  agencies,
  onSelectAgency,
}: {
  agencies: AgencyFeature[];
  onSelectAgency?: (ori: string, name: string) => void;
}) {
  const [webgl2] = useState(supportsWebGL2);
  if (!webgl2) return <AgencyListFallback agencies={agencies} onSelectAgency={onSelectAgency} />;
  return <MapCanvas agencies={agencies} onSelectAgency={onSelectAgency} />;
}

function MapCanvas({
  agencies,
  onSelectAgency,
}: {
  agencies: AgencyFeature[];
  onSelectAgency?: (ori: string, name: string) => void;
}) {
  const { theme } = useTheme();
  const c = useChartColors();
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const [tilesFailing, setTilesFailing] = useState(false);
  const loadedTheme = useRef(theme);
  // Keep the latest props in refs so the once-registered map listeners never
  // close over stale values (the refs update in an effect, not during render).
  const onSelect = useRef(onSelectAgency);
  const colors = useRef(c);
  const data = useRef<FeatureCollection>({
    type: "FeatureCollection",
    features: [],
  });
  const pendingFit = useRef(false);
  useEffect(() => {
    onSelect.current = onSelectAgency;
    colors.current = c;
  });

  // Create the map once. A theme change swaps the style in place (below).
  useEffect(() => {
    if (!container.current) return;
    const m = new MapLibreMap({
      container: container.current,
      style: BASEMAP[loadedTheme.current],
      center: [-98.5, 39.5], // continental US; fitBounds reframes to the data
      zoom: 3.2,
      attributionControl: { compact: true },
    });
    // Basemap failures (offline, blocked CDN) leave a blank map: say so.
    m.on("error", (e) => {
      console.warn("[map]", e.error?.message ?? String(e));
      if ((e as { sourceId?: string }).sourceId !== "agencies") setTilesFailing(true);
    });
    m.on("data", (e) => {
      if (e.dataType === "source" && (e as { isSourceLoaded?: boolean }).isSourceLoaded) {
        setTilesFailing(false);
      }
    });
    // A style load (the first one and each theme swap) drops our layers, so
    // add them again from the latest data and palette.
    m.on("style.load", () => {
      applyLayers(m, data.current, colors.current);
      if (pendingFit.current) {
        pendingFit.current = false;
        fitTo(m, data.current);
      }
    });
    // Layer-scoped listeners resolve at dispatch time, so they survive setStyle.
    m.on("click", "agencies-core", (e) => {
      const p = e.features?.[0]?.properties as { ori?: string; name?: string } | undefined;
      if (p?.ori) onSelect.current?.(p.ori, p.name ?? p.ori);
    });
    m.on("mouseenter", "agencies-core", () => {
      m.getCanvas().style.cursor = "pointer";
    });
    m.on("mouseleave", "agencies-core", () => {
      m.getCanvas().style.cursor = "";
    });
    map.current = m;
    // The panel starts at 0px during the first layout pass, so observe and
    // resize when it gets real dimensions.
    const ro = new ResizeObserver(() => m.resize());
    ro.observe(container.current);
    return () => {
      ro.disconnect();
      m.remove();
      map.current = null;
    };
  }, []);

  // Swap the basemap when the theme flips. This keeps the camera and the WebGL
  // context; the style.load handler re-adds the agency layers in the new palette.
  useEffect(() => {
    const m = map.current;
    if (!m || loadedTheme.current === theme) return;
    loadedTheme.current = theme;
    m.setStyle(BASEMAP[theme], { diff: false });
  }, [theme]);

  useEffect(() => {
    const m = map.current;
    data.current = {
      type: "FeatureCollection",
      features: toFeatures(agencies),
    };
    if (!m || agencies.length === 0) return;
    // Re-fit on every data change so switching region re-centers the map.
    if (m.isStyleLoaded()) {
      applyLayers(m, data.current, colors.current);
      fitTo(m, data.current);
    } else {
      pendingFit.current = true;
    }
  }, [agencies]);

  // h-full/w-full (not absolute): MapLibre forces position:relative on its
  // container via its own CSS, which would defeat `absolute inset-0`.
  return (
    <div className="relative h-full w-full">
      <div
        ref={container}
        className="h-full w-full"
        role="region"
        aria-label="Map of reporting agencies. Select a point to show that agency."
      />
      {tilesFailing && (
        <p
          role="status"
          className="mono absolute inset-x-2 bottom-8 bg-bg2/90 px-2 py-1 text-center text-[0.62rem] text-muted"
        >
          The map tiles are not loading (offline or blocked). Use “Find an agency” above.
        </p>
      )}
    </div>
  );
}

/** Shown when the device has no WebGL2: a plain list keeps drill-down usable. */
function AgencyListFallback({
  agencies,
  onSelectAgency,
}: {
  agencies: AgencyFeature[];
  onSelectAgency?: (ori: string, name: string) => void;
}) {
  const shown = agencies.slice(0, 200);
  return (
    <div className="flex h-full flex-col gap-2 overflow-hidden p-2">
      <p className="mono text-[0.65rem] text-muted">
        This device cannot show the map (WebGL2 is not available). Select an agency from the list.
      </p>
      <ul className="min-h-0 flex-1 overflow-y-auto" aria-label="Agencies">
        {shown.map((a) => (
          <li key={a.ori}>
            <button
              type="button"
              className="mono w-full cursor-pointer px-2 py-1 text-left text-[0.7rem] hover:text-accent"
              onClick={() => onSelectAgency?.(a.ori, a.agency_name ?? a.ori)}
            >
              {a.agency_name ?? a.ori}
            </button>
          </li>
        ))}
      </ul>
      {agencies.length > shown.length && (
        <p className="mono text-[0.6rem] text-muted">
          Showing {shown.length} of {agencies.length}. Choose a state to narrow the list.
        </p>
      )}
    </div>
  );
}
