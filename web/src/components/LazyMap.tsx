import { lazy, Suspense, useEffect, useRef, useState } from "react";
import type { AgencyFeature } from "../lib/api";
import { Empty } from "./Empty";

// MapLibre is about two thirds of the JavaScript. It loads only when the map
// panel comes near the viewport (on a phone the map is far below the fold).
const MapPanel = lazy(() => import("./MapPanel").then((m) => ({ default: m.MapPanel })));

export function LazyMap(props: {
  agencies: AgencyFeature[];
  onSelectAgency?: (ori: string, name: string) => void;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [near, setNear] = useState(() => typeof IntersectionObserver === "undefined");
  useEffect(() => {
    if (near || !box.current) return;
    const io = new IntersectionObserver(
      (entries) => entries.some((e) => e.isIntersecting) && setNear(true),
      { rootMargin: "200px" },
    );
    io.observe(box.current);
    return () => io.disconnect();
  }, [near]);
  const loading = <Empty state={{ isLoading: true, isError: false }} />;
  return (
    <div ref={box} className="h-full w-full">
      {near ? <Suspense fallback={loading}>{<MapPanel {...props} />}</Suspense> : loading}
    </div>
  );
}
