import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  outputDir: "../.runtime/playwright-results",
  reporter: [["list"], ["html", { outputFolder: "../.runtime/playwright-report", open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:5174",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "uv run --project .. --locked --extra dev --managed-python python -m uvicorn gov_erp.api:app --host 127.0.0.1 --port 8001 --no-access-log",
      url: "http://127.0.0.1:8001/health/ready",
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      timeout: 30_000,
      env: { GOVERP_API_PROXY: "http://127.0.0.1:8001" },
    },
  ],
});
