// Regenerate the local copy of the FBI CDE API docs.
//
// The docs page (https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi) is an
// Angular SPA whose Swagger spec is embedded as a minified JS object literal in
// a lazy-loaded webpack chunk. This script renders the page (for a screenshot +
// narrative text) and extracts the embedded OpenAPI spec into openapi.json.
//
// Usage (Playwright is a dev-only tool, not a project dependency):
//   npm i playwright && npx playwright install chromium
//   node fetch_cde_docs.mjs
import { chromium } from 'playwright';
import { writeFileSync } from 'node:fs';

const PAGE = 'https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi';
const OUT = new URL('../', import.meta.url); // docs/cde-api/

// Values inlined in the app's main.js that the embedded spec references via
// `Yr.c.apiSpec.*`. Update here if the FBI changes them.
const Yr = {
  c: {
    apiSpec: {
      info: { title: 'CDE-PRD-API-Gateway', version: '2022-10-13T17:58:35Z' },
      server: { url: 'https://api.usa.gov/crime/fbi/cde', basePath: '/LATEST' },
    },
  },
};

function extractObject(str, from) {
  let depth = 0, inStr = false, quote = '', esc = false;
  for (let k = from; k < str.length; k++) {
    const ch = str[k];
    if (inStr) {
      if (esc) esc = false;
      else if (ch === '\\') esc = true;
      else if (ch === quote) inStr = false;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === '`') { inStr = true; quote = ch; continue; }
    if (ch === '{') depth++;
    else if (ch === '}') { depth--; if (depth === 0) return str.slice(from, k + 1); }
  }
  return null;
}

const browser = await chromium.launch({ args: ['--no-sandbox'] });
const page = await browser.newPage({ viewport: { width: 1366, height: 2200 } });

// Sniff the lazy-loaded JS chunk that carries the embedded spec.
let specChunk = null;
page.on('response', async (r) => {
  if (specChunk || !/\.js(\?|$)/.test(r.url())) return;
  try {
    const t = (await r.body()).toString('utf8');
    if (/openapi\s*:/.test(t) && /\/summarized\/national/.test(t)) specChunk = t;
  } catch {}
});

await page.goto(PAGE, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
await page
  .waitForFunction(() => /api\.usa\.gov/i.test(document.body?.innerText || ''), { timeout: 45000 })
  .catch(() => {});
await page.waitForTimeout(1500);

writeFileSync(new URL('docApi-page.raw.txt', OUT), await page.evaluate(() => document.body.innerText));
await page.screenshot({ path: new URL('docApi.png', OUT).pathname, fullPage: true });

if (specChunk) {
  const i = specChunk.search(/openapi\s*:/);
  const literal = extractObject(specChunk, specChunk.lastIndexOf('{', i));
  const spec = new Function('Yr', 'return (' + literal + ')')(Yr);
  writeFileSync(new URL('openapi.json', OUT), JSON.stringify(spec, null, 2));
  console.log('openapi.json —', Object.keys(spec.paths).length, 'paths');
} else {
  console.warn('spec chunk not found — the bundle structure may have changed');
}

await browser.close();
