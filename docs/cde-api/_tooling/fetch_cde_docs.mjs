// Regenerate the local copy of the FBI CDE API docs.
//
// The docs page (https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi) is an
// Angular SPA whose Swagger spec is embedded as a minified JS object literal in
// a lazy-loaded webpack chunk. This script renders the page (for a screenshot +
// narrative text) and extracts the embedded OpenAPI spec into openapi.json.
//
// Safety: the script never runs code from the downloaded bundle. It parses the
// object literal with acorn and accepts only data nodes (objects, arrays,
// strings, numbers, booleans, null, the known `<name>.c.apiSpec.*` constants,
// and `+` between two strings). Any other node (a call, a function, another
// operator, an unknown reference) stops the script. The files
// are written to a scratch folder first, checked, and only then copied over
// the committed copy.
//
// Usage (dev-only tools, not project dependencies; pinned versions):
//   npm i --no-save playwright@1.65.1 acorn@8.19.0 && npx playwright install chromium
//   node fetch_cde_docs.mjs            # PW_CHROMIUM=<path> uses another Chromium
import { chromium } from 'playwright';
import { parseExpressionAt } from 'acorn';
import { copyFileSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const PAGE = 'https://cde.ucr.cjis.gov/LATEST/webapp/#/pages/docApi';
const OUT = new URL('../', import.meta.url); // docs/cde-api/
const SCRATCH = mkdtempSync(join(tmpdir(), 'cde-docs-'));

// Values inlined in the app's main.js that the embedded spec references via
// `<name>.c.apiSpec.*`. The minifier changes <name> in each build (`Yr` in
// 2026-06, `la` in 2026-11), so only the path after it is checked. Update the
// values here if the FBI changes them.
const API_SPEC = {
  info: { title: 'CDE-PRD-API-Gateway', version: '2022-10-13T17:58:35Z' },
  server: { url: 'https://api.usa.gov/crime/fbi/cde', basePath: '/LATEST' },
};

/** Find the end of the object literal that starts at `from` (string-aware). */
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

/** Turn an acorn AST of a literal into a value. Refuse every non-data node. */
export function toValue(node) {
  switch (node.type) {
    case 'ObjectExpression': {
      const obj = Object.create(null);
      for (const prop of node.properties) {
        if (prop.type !== 'Property' || prop.computed || prop.kind !== 'init' || prop.method) {
          throw new Error(`Refused property form at ${prop.start}`);
        }
        const key = prop.key.type === 'Identifier' ? prop.key.name : prop.key.value;
        if (typeof key !== 'string' && typeof key !== 'number') throw new Error(`Refused key at ${prop.start}`);
        if (key === '__proto__') throw new Error(`Refused key at ${prop.start}`);
        obj[key] = toValue(prop.value);
      }
      return obj;
    }
    case 'ArrayExpression':
      return node.elements.map((el) => {
        if (el === null || el.type === 'SpreadElement') throw new Error(`Refused array element at ${node.start}`);
        return toValue(el);
      });
    case 'Literal':
      if (node.regex || typeof node.bigint === 'string') throw new Error(`Refused literal at ${node.start}`);
      return node.value;
    case 'TemplateLiteral':
      if (node.expressions.length) throw new Error(`Refused template expression at ${node.start}`);
      return node.quasis[0].value.cooked;
    case 'UnaryExpression': // minifiers write !0 / !1 for booleans and void 0 for undefined
      if (node.argument.type === 'Literal' && typeof node.argument.value === 'number') {
        if (node.operator === '!') return !node.argument.value;
        if (node.operator === '-') return -node.argument.value;
        if (node.operator === 'void') return undefined;
      }
      throw new Error(`Refused operator ${node.operator} at ${node.start}`);
    case 'MemberExpression': {
      const path = [];
      let n = node;
      while (n.type === 'MemberExpression' && !n.computed && n.property.type === 'Identifier') {
        path.unshift(n.property.name);
        n = n.object;
      }
      if (n.type !== 'Identifier' || path[0] !== 'c' || path[1] !== 'apiSpec') {
        throw new Error(`Refused reference at ${node.start}`);
      }
      const value = path.slice(2).reduce((acc, k) => (Object.hasOwn(acc ?? {}, k) ? acc[k] : undefined), API_SPEC);
      if (typeof value !== 'string') throw new Error(`Unknown constant ${n.name}.${path.join('.')}`);
      return value;
    }
    case 'BinaryExpression': {
      // Only string concatenation, for example `x.c.apiSpec.server.url + "/{basePath}"`.
      const left = node.operator === '+' ? toValue(node.left) : undefined;
      const right = node.operator === '+' ? toValue(node.right) : undefined;
      if (typeof left !== 'string' || typeof right !== 'string') throw new Error(`Refused operator at ${node.start}`);
      return left + right;
    }
    default:
      throw new Error(`Refused ${node.type} at ${node.start}`);
  }
}

function checkSpec(spec) {
  const paths = Object.keys(spec?.paths ?? {});
  if (!/^3\./.test(spec?.openapi ?? '')) throw new Error('openapi.json: not an OpenAPI 3 document');
  if (paths.length < 30) throw new Error(`openapi.json: only ${paths.length} paths (expected about 39)`);
  if (!paths.some((p) => p.startsWith('/summarized/'))) throw new Error('openapi.json: no /summarized path');
}

const browser = await chromium.launch({ executablePath: process.env.PW_CHROMIUM || undefined });
try {
  const page = await browser.newPage({ viewport: { width: 1366, height: 2200 } });

  // Sniff the lazy-loaded JS chunk that carries the embedded spec (as text only).
  let specChunk = null;
  page.on('response', async (r) => {
    if (specChunk || !/\.js(\?|$)/.test(r.url())) return;
    try {
      const t = (await r.body()).toString('utf8');
      if (/openapi\s*:/.test(t) && /\/summarized\/national/.test(t)) specChunk = t;
    } catch {
      // The body of a redirect or an aborted response is not available.
    }
  });

  await page.goto(PAGE, { waitUntil: 'networkidle', timeout: 60000 }).catch(() => {});
  await page
    .waitForFunction(() => /api\.usa\.gov/i.test(document.body?.innerText || ''), { timeout: 45000 })
    .catch(() => {});
  await page.waitForTimeout(1500);

  const text = await page.evaluate(() => document.body.innerText);
  if (!/api\.usa\.gov/i.test(text)) throw new Error('The docs page did not render');
  writeFileSync(join(SCRATCH, 'docApi-page.raw.txt'), text);
  await page.screenshot({ path: join(SCRATCH, 'docApi.png'), fullPage: true });

  if (!specChunk) throw new Error('Spec chunk not found: the bundle structure may have changed');
  const i = specChunk.search(/openapi\s*:/);
  const literal = extractObject(specChunk, specChunk.lastIndexOf('{', i));
  if (!literal) throw new Error('Spec literal not found');
  const spec = toValue(parseExpressionAt(literal, 0, { ecmaVersion: 'latest' }));
  checkSpec(spec);
  writeFileSync(join(SCRATCH, 'openapi.json'), JSON.stringify(spec, null, 2));

  // Every file is checked: copy them over the committed copy.
  for (const name of ['docApi-page.raw.txt', 'docApi.png', 'openapi.json']) {
    copyFileSync(join(SCRATCH, name), new URL(name, OUT));
  }
  console.log('openapi.json:', Object.keys(JSON.parse(readFileSync(join(SCRATCH, 'openapi.json'))).paths).length, 'paths');
} finally {
  await browser.close();
}
