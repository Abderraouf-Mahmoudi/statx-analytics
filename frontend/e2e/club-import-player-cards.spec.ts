import { expect, test } from "@playwright/test";

test("tablet administrator selects a Tunisian club without live provider calls", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.route("**/api/v1/integrations/api-football/status", async (route) => route.fulfill({ json: { configured: true, calls_used: 0, remaining: 90, selected_team: null, last_run: null } }));
  await page.route("**/api/v1/integrations/api-football/tunisia/clubs", async (route) => route.fulfill({ json: { stale: false, clubs: [
    { provider_id: "1001", name: "Espérance ST", logo_url: null, league_provider_id: "202", league_name: "Ligue 1", season: 2026 },
    { provider_id: "1002", name: "Club Africain", logo_url: null, league_provider_id: "202", league_name: "Ligue 1", season: 2026 },
  ] } }));
  await page.route("**/api/v1/integrations/api-football/select-club", async (route) => route.fulfill({ status: 202, json: { public_id: "run-e2e", status: "queued", call_count: 0, remaining_quota: 90, result_summary: null, error_summary: null } }));
  await page.route("**/api/v1/integrations/api-football/sync-runs/run-e2e", async (route) => route.fulfill({ json: { public_id: "run-e2e", status: "completed", call_count: 3, remaining_quota: 87, result_summary: { teams: 2, players: 28, fixtures: 12, standings: 1, absent: 0 }, error_summary: null } }));

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Connexion StatX" })).toBeVisible();
  await page.getByLabel("Adresse e-mail").fill("admin@statx.local");
  await page.getByLabel("Mot de passe").fill("A-secure-local-passphrase-2026");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await expect(page.getByRole("heading", { name: "Choisir votre club tunisien" })).toBeVisible();
  await page.getByRole("searchbox", { name: "Rechercher un club" }).fill("Espérance");
  await page.getByRole("button", { name: "Choisir Espérance ST" }).click();
  await page.getByRole("button", { name: "Confirmer et importer" }).click();
  await expect(page.getByText("28 joueurs importés")).toBeVisible();
  await page.getByRole("button", { name: "Ouvrir StatX" }).click();
  await expect(page.getByRole("heading", { name: "Centre opérationnel StatX" })).toBeVisible();
});
