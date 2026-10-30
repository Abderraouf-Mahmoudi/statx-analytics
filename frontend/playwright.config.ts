import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  use: { baseURL: "http://127.0.0.1:5173" },
  webServer: [
    { command: "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-e2e-backend.ps1", url: "http://127.0.0.1:8000/health", reuseExistingServer: false },
    { command: "npm run dev -- --host 127.0.0.1", url: "http://127.0.0.1:5173", reuseExistingServer: true },
  ],
});
