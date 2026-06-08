# web — OpenHydra dashboard

A command-center style **React + Vite + TypeScript** dashboard over the FastAPI
service — dark HUD aesthetic with neon panels, live offense-rate & clearance
trends (Recharts), arrest demographics, and a glowing **MapLibre GL** map of
reporting agencies (NIBRS vs SRS).

![OpenHydra dashboard](../docs/dashboard.png)

## Run

```bash
# 1) start the API (serves the DuckDB marts) — from the repo root:
cd api && uv run oh-api                 # http://127.0.0.1:8000

# 2) start the dashboard:
cd web && npm install && npm run dev    # http://localhost:5173 (proxies /api -> :8000)
```

The Vite dev server proxies `/api` to the FastAPI service, so no CORS issue or
API key is exposed to the browser.

## Stack

React 19 · Vite · TypeScript · TanStack Query · Tailwind v4 · Recharts · MapLibre GL.

## Develop

```bash
npm run build   # tsc -b + vite build
npm run lint    # eslint
```

## Layout

```
src/
  App.tsx                dashboard grid
  lib/                   api.ts (typed client), queries.ts (TanStack Query), format.ts
  components/            TopBar, Controls, StatTile, Panel, MapPanel
  components/charts/     TrendChart, ClearanceChart, ArrestsChart, DarkTooltip
```
