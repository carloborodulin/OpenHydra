import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Feature, FeatureCollection, Point } from "geojson";
import { useEffect, useRef } from "react";
import type { AgencyFeature } from "../lib/api";
import { useChartColors, useTheme } from "../lib/theme";

const BASEMAP = {
  dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
  light: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
};

export function MapPanel({
  agencies,
  onSelectAgency,
}: {
  agencies: AgencyFeature[];
  onSelectAgency?: (ori: string, name: string) => void;
}) {
  const { theme } = useTheme();
  const c = useChartColors();
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  // Keep the latest callback in a ref so the once-registered map listeners
  // never close over a stale prop (updated in an effect, not during render).
  const onSelect = useRef(onSelectAgency);
  useEffect(() => {
    onSelect.current = onSelectAgency;
  });

  // Re-initialize the map when the theme flips so it picks up the new basemap;
  // the cleanup below tears down the old instance first.
  useEffect(() => {
    if (!container.current || map.current) return;
    const m = new maplibregl.Map({
      container: container.current,
      style: BASEMAP[theme],
      center: [-98.5, 39.5], // continental US; fitBounds reframes to the data
      zoom: 3.2,
      attributionControl: { compact: true },
    });
    m.on("error", (e) => console.error("[map]", e.error?.message ?? String(e)));
    m.on("load", () => m.resize());
    // Click a point to drill into that agency; the layer is added later, but a
    // layer-scoped listener is resolved at dispatch time so registering here is
    // safe and runs only once.
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
    // MapLibre has no built-in resize handling; the panel starts at 0px during
    // the first layout pass, so observe and resize when it gets real dimensions.
    const ro = new ResizeObserver(() => m.resize());
    ro.observe(container.current);
    return () => {
      ro.disconnect();
      m.remove();
      map.current = null;
    };
  }, [theme]);

  useEffect(() => {
    const m = map.current;
    if (!m || agencies.length === 0) return;

    // Sanity-bound to US lon/lat: drops mis-geocoded points (e.g. an agency at
    // -9,-9) and the lone Aleutian outpost past the antimeridian that would
    // otherwise stretch fitBounds across the whole globe.
    const inUS = (lat: number, lon: number) =>
      lon >= -180 && lon <= -64 && lat >= 15 && lat <= 72;
    const features: Feature[] = agencies
      .filter((a) => a.latitude != null && a.longitude != null)
      .filter((a) => inUS(a.latitude as number, a.longitude as number))
      .map((a) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [a.longitude as number, a.latitude as number] },
        properties: { nibrs: a.is_nibrs ? 1 : 0, name: a.agency_name, ori: a.ori },
      }));
    const data: FeatureCollection = { type: "FeatureCollection", features };

    const apply = () => {
      const src = m.getSource("agencies") as maplibregl.GeoJSONSource | undefined;
      if (src) {
        src.setData(data);
      } else {
        m.addSource("agencies", { type: "geojson", data });
        m.addLayer({
          id: "agencies-glow",
          type: "circle",
          source: "agencies",
          paint: {
            "circle-radius": 16,
            "circle-blur": 1,
            "circle-opacity": 0.5,
            "circle-color": ["case", ["==", ["get", "nibrs"], 1], c.accent, c.violet],
          },
        });
        m.addLayer({
          id: "agencies-core",
          type: "circle",
          source: "agencies",
          paint: {
            "circle-radius": 4,
            "circle-color": ["case", ["==", ["get", "nibrs"], 1], c.good, c.alert],
            "circle-stroke-color": c.bg,
            "circle-stroke-width": 0.6,
          },
        });
      }
      // Re-fit on every data change so switching region re-centers the map.
      const lons = features.map((f) => (f.geometry as Point).coordinates[0]);
      const lats = features.map((f) => (f.geometry as Point).coordinates[1]);
      if (lons.length) {
        m.fitBounds(
          [
            [Math.min(...lons), Math.min(...lats)],
            [Math.max(...lons), Math.max(...lats)],
          ],
          { padding: 48, duration: 900, maxZoom: 8 },
        );
      }
    };

    if (m.isStyleLoaded()) apply();
    else m.once("load", apply);
    // `c` re-runs this after a theme rebuild so markers are re-added with the
    // new palette on the fresh basemap (it's memoized, so stable within a theme).
  }, [agencies, c]);

  // h-full/w-full (not absolute): MapLibre forces position:relative on its
  // container via its own CSS, which would defeat `absolute inset-0`.
  return <div ref={container} className="h-full w-full" />;
}
