# FBI CDE API — local reference copy

A local, offline copy of the FBI Crime Data Explorer API documentation, for
building OpenHydra without re-scraping the live site.

**Source:** <https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi>
**Captured:** 2026-06-08
**Spec version:** OpenAPI 3.0.1 — `CDE-PRD-API-Gateway` (`2022-10-13T17:58:35Z`)

## Contents

| File | What it is |
|---|---|
| [`openapi.json`](./openapi.json) | **The full machine-readable spec** — 39 paths, 26 schemas, all parameters & responses. Primary reference. |
| [`endpoints.md`](./endpoints.md) | Human-readable index generated from the spec (paths grouped by tag, with params + responses). |
| [`docApi-page.md`](./docApi-page.md) | The docApi page's narrative + endpoint catalog, transcribed verbatim (group descriptions live here, not in the spec). |
| [`docApi.png`](./docApi.png) | Full-page screenshot of the rendered docs. |
| [`docApi-page.raw.txt`](./docApi-page.raw.txt) | Raw `innerText` of the rendered page (unedited). |
| [`_tooling/`](./_tooling) | Scripts to regenerate everything above. |

## Key facts

- **Base URL:** `https://api.usa.gov/crime/fbi/cde` (server variable `basePath`, default `/LATEST`).
- **Auth:** append `?API_KEY=<key>` to every request (read-only; returns JSON or CSV).
- **Reporting systems:** SRS (legacy aggregate counts) and NIBRS (incident-based).
- **11 endpoint groups:** Agency, Arrest, Expanded Homicide (`/shr`), Expanded
  Property (`/supplemental`), Hate Crime, Law Enforcement Employees (`/pe`),
  LESDC, NIBRS, NIBRS Estimations, Summarized, Use Of Force.

### Notes / discrepancies observed against the live API

- Law Enforcement Employees: only the **canonical** spec paths `/pe`,
  `/pe/{state}`, `/pe/{state}/{ori}` return real data. The `/pe/national` and
  `/pe/state/{state}` variants answer `200` but return **all-`null`** values — do
  not use them (this earlier bit `cdeclient`, which now uses the canonical forms).
- `/agency/{query}/{value}` is generic — `cdeclient` uses the `byStateAbbr`
  query (`/agency/byStateAbbr/{ST}`), which the live API accepts.
- `/pe` endpoints take 4-digit **years**; most others take **`MM-YYYY`**.
- The gateway intermittently returns `503`; clients should retry.

## Regenerating

The docs page is an Angular SPA whose Swagger spec is embedded as a minified JS
object literal in a lazy-loaded webpack chunk (it is **not** fetched as a spec
file). The tooling renders the page headless and extracts the embedded spec.

```bash
cd docs/cde-api/_tooling
npm i playwright && npx playwright install chromium   # dev-only, not a project dep
node fetch_cde_docs.mjs     # -> openapi.json, docApi.png, docApi-page.raw.txt
node gen_endpoints.mjs      # -> endpoints.md
```
