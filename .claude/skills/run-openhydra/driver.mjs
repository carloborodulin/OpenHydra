// OpenHydra browser-walkthrough driver — drives the running app's 8 tabs and
// screenshots each. See SKILL.md for how to launch the server + invoke this.
//
// The app is a single-page app that switches views via React state (NOT URL
// routes), so every tab lives at "/" — we navigate by clicking nav buttons.
//
// playwright-core isn't a repo dependency; install it in a temp dir and point
// PW_DIR at that dir (see SKILL.md). It drives the cached chromium-1223.
import { createRequire } from "node:module";
import { mkdirSync } from "node:fs";

const require = createRequire(process.env.PW_DIR ? `${process.env.PW_DIR}/_.cjs` : import.meta.url);
const { chromium } = require("playwright-core");

const BASE = process.env.BASE || "http://127.0.0.1:8146";
const OUT = process.env.SHOTS || "/tmp/openhydra-shots";
mkdirSync(OUT, { recursive: true });

const TABS = [
  "Overview",
  "Hate Crime",
  "Homicide",
  "Property",
  "NIBRS",
  "NIBRS Est.",
  "Use of Force",
  "LESDC",
];

const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const page = await (
  await browser.newContext({ viewport: { width: 1680, height: 1000 } })
).newPage();

const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
page.on("pageerror", (e) => errors.push("pageerror: " + e.message));

await page.goto(BASE, { waitUntil: "load", timeout: 30000 });
await page.getByText("OPENHYDRA").first().waitFor({ timeout: 20000 });

let failures = 0;
for (const tab of TABS) {
  try {
    // exact:true so "NIBRS" doesn't also match "NIBRS Est."
    await page.locator("nav").getByRole("button", { name: tab, exact: true }).click();
  } catch {
    /* Overview is the default view; a missed click just leaves it active */
  }
  try {
    await page.waitForSelector("svg.recharts-surface", { timeout: 15000 });
  } catch {
    /* screenshot whatever rendered even if no chart appeared */
  }
  await page.waitForTimeout(1000); // recharts animate + React Query settles
  const charts = await page.locator("svg.recharts-surface").count();
  const noData = await page.getByText("No Data").count();
  const file = `${OUT}/${tab.replace(/[^a-z0-9]+/gi, "_").toLowerCase()}.png`;
  await page.screenshot({ path: file });
  const ok = charts > 0 && noData === 0;
  if (!ok) failures++;
  console.log(`${ok ? "OK " : "!! "}${tab.padEnd(14)} charts=${charts} noData=${noData} -> ${file}`);
}

console.log("console errors:", errors.length ? JSON.stringify(errors.slice(0, 8)) : "none");
await browser.close();
process.exit(failures === 0 && errors.length === 0 ? 0 : 1);
