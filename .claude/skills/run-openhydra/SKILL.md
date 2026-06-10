---
name: run-openhydra
description: Run, launch, serve, and screenshot the OpenHydra app (FBI CDE crime dashboard — FastAPI API + React/Vite SPA over a DuckDB warehouse). Use to start the app, do a browser walkthrough of its tabs, screenshot a view, or smoke-test that every domain renders.
---

# Run OpenHydra

OpenHydra is a 4-layer app: `cdeclient` (CDE API client) → `warehouse`
(dbt→DuckDB) → `api` (FastAPI) → `web` (React/Vite SPA). The fastest way to see
it whole is **one process**: build the SPA and serve it through the API, which
mounts `web/dist` at `/` when `OPENHYDRA_STATIC_DIR` is set. Then drive the
running app with the committed Playwright driver:
`.claude/skills/run-openhydra/driver.mjs`.

All paths below are relative to the repo root. Tools used: `uv`, `node`/`npm`,
`curl`, `python3` (already present).

## Build the SPA

```bash
cd web && npm ci && npm run build && cd ..   # → web/dist (tsc -b && vite build)
```

`npm ci` is only needed once (or after dependency changes); thereafter just
`npm run build`.

## Serve (API + built SPA, one supervised process)

The committed warehouse `warehouse/openhydra.duckdb` already holds data for every
domain, so no ETL is needed to run the app. (To rebuild it from the committed
seeds: `cd warehouse/dbt && uv run --group dbt dbt build --profiles-dir .`.)

```bash
# FBI_CDE_API_KEY is only needed for live agency drill-down; the warehouse views
# work without it. Extract it from .env WITHOUT `source` (sourcing .env clobbers PATH).
export FBI_CDE_API_KEY=$(python3 -c "
for l in open('.env'):
    l=l.strip()
    if l.startswith('FBI_CDE_API_KEY='):
        print(l.split('=',1)[1].strip().strip(chr(34)).strip(chr(39))); break
")
export OPENHYDRA_STATIC_DIR="$PWD/web/dist"   # makes the API serve the SPA at /
uv run --directory api python -m uvicorn openhydra_api.main:app --port 8146 --log-level warning &
SRV=$!; trap 'kill $SRV 2>/dev/null' EXIT      # always kill the server on exit
curl --retry 40 --retry-delay 1 --retry-connrefused -sf http://127.0.0.1:8146/health  # poll, don't sleep
```

The SPA is now at <http://127.0.0.1:8146/>; the API is under `/api/*`.

## Drive (agent path — browser walkthrough)

`chromium-cli` isn't installed, but Playwright's Chromium is cached
(`~/Library/Caches/ms-playwright/chromium-1223`). Install `playwright-core` in a
temp dir (never `$HOME`) and point `PW_DIR` at it; the driver resolves
`playwright-core` from there and drives the cached Chromium by default.

```bash
mkdir -p /tmp/oh-pw && (cd /tmp/oh-pw && npm init -y >/dev/null && npm install playwright-core@latest >/dev/null)
PW_DIR=/tmp/oh-pw BASE=http://127.0.0.1:8146 SHOTS=/tmp/openhydra-shots \
  node .claude/skills/run-openhydra/driver.mjs
```

The driver clicks through all 8 tabs (Overview, Hate Crime, Homicide, Property,
NIBRS, NIBRS Est., Use of Force, LESDC), waits for each chart, and writes one PNG
per tab to `$SHOTS`. It prints `OK`/`!!` per tab and **exits non-zero** if any tab
has no chart, shows "No Data", or logs a console error — so it doubles as a smoke
test. **Look at the screenshots** (e.g. `$SHOTS/overview.png`); a blank frame is a
failure even if the count looks fine.

Verified result (this machine): all 8 tabs `OK`, `console errors: none`.

## Run (human path)

For live editing, run the API and the Vite dev server separately (Vite proxies
`/api` to the API). This is a watcher — supervise it and kill it when done; don't
leave it running.

```bash
uv run --directory api python -m uvicorn openhydra_api.main:app --port 8000 &   # API
cd web && npm run dev   # Vite on :5173 — Ctrl-C to stop
```

## Gotchas

- **`source .env` breaks the shell** — it clobbers `PATH` (so `curl`/`node`
  vanish). Extract values with the `python3` snippet above instead.
- **SPA uses tab state, not routes** — every view is at `/`. You can't deep-link a
  tab; you must click its nav button. The driver uses
  `getByRole("button", { name, exact: true })` — `exact:true` matters so `NIBRS`
  doesn't also match `NIBRS Est.`.
- **`OPENHYDRA_STATIC_DIR` is read at import time** — export it *before* launching
  uvicorn, or the SPA mount won't register.
- **Recharts animate** — wait ~1s after `svg.recharts-surface` appears before
  screenshotting, or bars/lines are mid-transition.
- **Data coverage** — national + all states/regions for the warehouse groups;
  LESDC is national-only (2022–2023), Use of Force national-only (2019–2023),
  NIBRS Estimations national+region only (2022). Per-agency views need
  `FBI_CDE_API_KEY` (live CDE proxy).

## Test

```bash
for pkg in cdeclient warehouse api; do uv run --directory "$pkg" pytest -q; done
cd web && npm run lint && npm run build   # frontend has no unit tests; lint+build is the gate
```

## Troubleshooting

- **`/health` never responds** → the API failed to import. Run uvicorn in the
  foreground (drop `&`) to see the traceback (often a missing `FBI_CDE_API_KEY`
  for live routes, or `warehouse/openhydra.duckdb` absent — rebuild it with dbt).
- **Driver: `Cannot find package 'playwright-core'`** → `PW_DIR` is unset or points
  at a dir without `node_modules/playwright-core`. Re-run the temp install.
- **Driver: every tab `!! noData`** → the warehouse DB is empty/missing; rebuild it
  with the dbt command above (or repopulate via `oh-etl pull`).
