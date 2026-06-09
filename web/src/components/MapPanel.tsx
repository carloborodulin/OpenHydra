import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Feature, FeatureCollection, Point } from "geojson";
import { useEffect, useRef } from "react";
import type { AgencyFeature } from "../lib/api";

const STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export function MapPanel({ agencies }: { agencies: AgencyFeature[] }) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);

  useEffect(() => {
    if (!container.current || map.current) return;
    const m = new maplibregl.Map({
      container: container.current,
      style: STYLE,
      center: [-98.5, 39.5], // continental US; fitBounds reframes to the data
      zoom: 3.2,
      attributionControl: { compact: true },
    });
    m.on("error", (e) => console.error("[map]", e.error?.message ?? String(e)));
    m.on("load", () => m.resize());
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
  }, []);

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
        properties: { nibrs: a.is_nibrs ? 1 : 0, name: a.agency_name },
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
            "circle-color": ["case", ["==", ["get", "nibrs"], 1], "#22d3ee", "#a78bfa"],
          },
        });
        m.addLayer({
          id: "agencies-core",
          type: "circle",
          source: "agencies",
          paint: {
            "circle-radius": 4,
            "circle-color": ["case", ["==", ["get", "nibrs"], 1], "#3df5b0", "#ff5470"],
            "circle-stroke-color": "#04070d",
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
  }, [agencies]);

  // h-full/w-full (not absolute): MapLibre forces position:relative on its
  // container via its own CSS, which would defeat `absolute inset-0`.
  return <div ref={container} className="h-full w-full" />;
}
