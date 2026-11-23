import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";

// One assertion per view: a panel title that only that view has.
const VIEWS: { id: string; tab: string; expect: RegExp }[] = [
  { id: "overview", tab: "Overview", expect: /Offense Rate · Homicide/ },
  { id: "performance", tab: "Performance", expect: /Volume vs Clearance/ },
  { id: "hate-crime", tab: "Hate Crime", expect: /Bias Category/ },
  { id: "homicide", tab: "Homicide", expect: /Circumstance/ },
  { id: "property", tab: "Property", expect: /Stolen Value/ },
  { id: "nibrs", tab: "NIBRS", expect: /Location ·/ },
  { id: "nibrs-estimation", tab: "NIBRS Est.", expect: /Victim/ },
  { id: "use-of-force", tab: "Use of Force", expect: /Report Metrics/ },
  { id: "lesdc", tab: "LESDC", expect: /Suicides ·/ },
  { id: "methodology", tab: "Methodology", expect: /Methodology and definitions/ },
];

function watchErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => {
    if (m.type() === "error" && !/tiles\.basemaps|cartocdn/.test(m.text())) errors.push(m.text());
  });
  return errors;
}

async function openView(page: Page, tab: string, mobile: boolean) {
  if (mobile) {
    await page.getByRole("button", { name: "Open navigation menu" }).click();
    await page
      .getByRole("dialog", { name: "Views" })
      .getByRole("button", { name: tab, exact: true })
      .click();
  } else {
    await page
      .getByRole("navigation", { name: "Views" })
      .getByRole("button", { name: tab, exact: true })
      .click();
  }
}

for (const theme of ["light", "dark"] as const) {
  test.describe(`${theme} theme`, () => {
    test.beforeEach(async ({ page }) => {
      await page.addInitScript((t) => localStorage.setItem("oh-theme", t), theme);
    });

    test("every view renders its own data, with no errors and no axe violations", async ({
      page,
    }, info) => {
      const mobile = info.project.name === "mobile";
      const errors = watchErrors(page);
      await page.goto("/");
      for (const v of VIEWS) {
        await openView(page, v.tab, mobile);
        await expect(page).toHaveURL(
          v.id === "overview" ? /\/(\?.*)?$/ : new RegExp(`view=${v.id}`),
        );
        await expect(page.getByRole("heading", { name: v.expect }).first()).toBeVisible();
        if (v.id !== "methodology") {
          await expect(page.locator("svg.recharts-surface").first()).toBeVisible();
        }
        await expect(page.getByRole("alert")).toHaveCount(0);
        const axe = await new AxeBuilder({ page }).exclude(".maplibregl-canvas").analyze();
        expect(axe.violations.map((x) => `${v.id}: ${x.id}`)).toEqual([]);
      }
      expect(errors).toEqual([]);
    });
  });
}

test("the mobile drawer is a keyboard-safe dialog", async ({ page }, info) => {
  test.skip(info.project.name !== "mobile", "the drawer exists only below the desktop width");
  await page.goto("/");
  const menu = page.getByRole("button", { name: "Open navigation menu" });
  await menu.focus();
  for (let i = 0; i < 5; i++) {
    await page.keyboard.press("Tab");
    expect(await page.evaluate(() => !!document.activeElement?.closest("#nav-drawer"))).toBe(false);
  }
  await menu.click();
  await expect(page.getByRole("button", { name: "Close navigation" })).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  expect(await page.evaluate(() => !!document.activeElement?.closest("#nav-drawer"))).toBe(true);
  await page.keyboard.press("Escape");
  await expect(menu).toBeFocused();
});

test("the URL keeps the state, and a region change clears the agency", async ({ page }, info) => {
  test.skip(info.project.name !== "desktop", "one viewport is enough for the state logic");
  await page.goto("/?region=NY");
  await expect(page.getByRole("combobox", { name: /^Region: New York/ })).toBeVisible();
  const search = page.getByRole("combobox", { name: /find an agency/i });
  await search.fill("buffalo");
  await search.press("Enter");
  await expect(page).toHaveURL(/agency=NY/);
  await page.getByRole("combobox", { name: /^Region:/ }).focus();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.type("tex");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/region=TX/);
  await expect(page).not.toHaveURL(/agency=/);
  await page.goBack();
  await expect(page).toHaveURL(/region=NY.*agency=NY|agency=NY.*region=NY/);
});

test("the map draws agencies and opens one on click", async ({ page }) => {
  const errors = watchErrors(page);
  await page.goto("/");
  await page.getByRole("combobox", { name: /find an agency/i }).scrollIntoViewIfNeeded();
  const canvas = page.locator("canvas.maplibregl-canvas");
  await expect(canvas).toBeVisible();
  await canvas.scrollIntoViewIfNeeded();
  await page.waitForTimeout(4000);
  const box = await canvas.boundingBox();
  expect(box).not.toBeNull();
  let opened = false;
  for (let y = 0.3; y <= 0.7 && !opened; y += 0.05) {
    for (let x = 0.3; x <= 0.8 && !opened; x += 0.025) {
      await page.mouse.click(box!.x + box!.width * x, box!.y + box!.height * y);
      opened = (await page.getByRole("button", { name: /^✕/ }).count()) > 0;
    }
  }
  expect(opened).toBe(true);
  expect(errors).toEqual([]);
});
