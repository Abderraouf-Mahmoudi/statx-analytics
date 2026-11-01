import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  projects: [
    {
      name: "bootstrap",
      testMatch: /setup-login\.spec\.ts/,
    },
    {
      name: "application",
      dependencies: ["bootstrap"],
      testMatch: /(roster-rtl-touch|club-import-player-cards|player-photo-touch|setup-club-import|player-lifecycle)\.spec\.ts/,
    },
  ],
  use: { baseURL: "http://127.0.0.1:15173" },
  webServer: [
    { command: "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-e2e-backend.ps1", url: "http://127.0.0.1:18000/health", reuseExistingServer: false },
    { command: "npm run dev -- --host 127.0.0.1 --port 15173", url: "http://127.0.0.1:15173", reuseExistingServer: false, env: { VITE_API_URL: "http://127.0.0.1:18000/api/v1" } },
  ],
});
