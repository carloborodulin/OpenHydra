import { defineConfig, devices } from "@playwright/test";

// Browser tests against a running server (the API serving web/dist):
//   make data web && make serve PORT=8146   (another terminal)
//   BASE_URL=http://127.0.0.1:8146 npx playwright test
// CI starts the server first (see .github/workflows/ci.yml).
const chromium = {
  ...devices["Desktop Chrome"],
  // Headless CI machines have no GPU: SwiftShader gives the map its WebGL2.
  launchOptions: {
    args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
    executablePath: process.env.PW_CHROMIUM || undefined,
  },
};

export default defineConfig({
  testDir: "e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: true,
  workers: process.env.CI ? 2 : 3,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.BASE_URL ?? "http://127.0.0.1:8146",
    trace: "retain-on-failure",
    // No fade-in animations: axe would measure contrast in the middle of one.
    reducedMotion: "reduce",
  },
  projects: [
    { name: "desktop", use: { ...chromium, viewport: { width: 1440, height: 900 } } },
    {
      name: "mobile",
      use: { ...chromium, viewport: { width: 390, height: 844 }, isMobile: false, hasTouch: true },
    },
  ],
});
