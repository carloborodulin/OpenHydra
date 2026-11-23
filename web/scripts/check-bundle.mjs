// Fail the build when the JavaScript that loads at startup is too large.
// It reads dist/index.html, follows the entry script and its static imports
// (modulepreload links), and sums their gzip sizes. Chunks that load later
// (each view, the map) are reported but not counted.
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { gzipSync } from "node:zlib";

const BUDGET_KB = Number(process.env.JS_BUDGET_KB ?? 300);
const dist = new URL("../dist/", import.meta.url).pathname;
const html = readFileSync(join(dist, "index.html"), "utf8");
const initial = new Set(
  [...html.matchAll(/(?:src|href)="\/(assets\/[^"]+\.js)"/g)].map((m) => m[1]),
);
const gz = (file) => gzipSync(readFileSync(join(dist, file))).length / 1024;

let total = 0;
for (const f of initial) {
  const kb = gz(f);
  total += kb;
  console.log(`initial  ${kb.toFixed(1).padStart(7)} kB  ${f}`);
}
for (const f of readdirSync(join(dist, "assets")).filter((f) => f.endsWith(".js"))) {
  if (!initial.has(`assets/${f}`)) console.log(`lazy     ${gz(`assets/${f}`).toFixed(1).padStart(7)} kB  assets/${f}`);
}
console.log(`initial JavaScript: ${total.toFixed(1)} kB gzip (budget ${BUDGET_KB} kB)`);
if (total > BUDGET_KB) {
  console.error("Over budget: split the code or remove a dependency.");
  process.exit(1);
}
