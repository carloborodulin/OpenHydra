# FBI CDE API — local reference copy

A local, offline copy of the FBI Crime Data Explorer API documentation, for
building OpenHydra without re-scraping the live site.

**Source:** <https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi>
**Captured:** 2026-11-23 (first copy 2026-06-08)
**Spec version:** OpenAPI 3.0.1 — `CDE-PRD-API-Gateway` (`2022-10-13T17:58:35Z`)

## Contents

| File | What it is |
|---|---|
| [`openapi.json`](./openapi.json) | **The full machine-readable spec**: 32 paths, 22 schemas, all parameters and responses. Primary reference. |
| [`endpoints.md`](./endpoints.md) | Human-readable index generated from the spec (paths grouped by tag, with params + responses). |
| [`docApi-page.md`](./docApi-page.md) | The docApi page's narrative and endpoint catalog of 2026-06-08, transcribed verbatim (group descriptions live here, not in the spec). |
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

### Changes in the FBI API from 2026-06 to 2026-11

The spec went from 39 to 32 paths. The changes that affect OpenHydra:

- The national UoF participation routes are gone: `/participation/national/uof/{query}`,
  `/participation/national/{collection}/{query}` and
  `/participation/state/{state}/{collection}/{query}`. The live API returns 404 for them.
  The OpenHydra extract keeps the last good UoF data (see the `fbi contract` workflow).
- A new route `/uof?year=YYYY&location=<state>` gives the participation of one state
  (`par_agencies`, `total_agencies`, `percent_agencies`). For an agency ORI it returns `null`.
  It has no national total.
- The `/uof/questions/...` and `/uof/reports/...` routes are gone.
- The hate crime routes without `{bias}` are gone from the spec, and the `{bias}` routes
  now require a `type` parameter. The routes without `{bias}` still answer.
- On the docs page, the endpoint groups are now collapsed, so `docApi-page.raw.txt`
  holds no endpoint list. Use `openapi.json` or `endpoints.md`.

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

The script does not run code from the downloaded bundle. It parses the object
literal with acorn and accepts only data (literals, objects, arrays, string
concatenation and the known `c.apiSpec.*` constants). It writes to a temporary
folder, checks the spec, and only then replaces the files here.

```bash
cd docs/cde-api/_tooling
npm i --no-save playwright@1.65.1 acorn@8.19.0 && npx playwright install chromium   # dev-only
node fetch_cde_docs.mjs     # -> openapi.json, docApi.png, docApi-page.raw.txt
node gen_endpoints.mjs      # -> endpoints.md
```
