import { expect, test } from "@playwright/test";

test("tablet first-run selects a Tunisian club and queues import in one setup", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.route("**/api/v1/setup/status", (route) => route.fulfill({ json: { required: true } }));
  await page.route("**/api/v1/setup/provider-catalog", (route) => route.fulfill({ json: { stale: false, quota: { calls_used: 2, remaining: 88 }, clubs: [
    { provider_id: "1001", name: "Espérance ST", logo_url: null, league_provider_id: "202", league_name: "Ligue 1", season: 2026 },
  ] } }));
  let setupPayload: Record<string, unknown> | null = null;
  await page.route("**/api/v1/setup", async (route) => { setupPayload = await route.request().postDataJSON(); await route.fulfill({ status: 201, json: { user_id: "u1", organization_id: "o1", display_name: "Coach StatX", email: "coach@statx.local", role: "admin", job_title: "coach", locale: "fr" } }); });
  await page.route("**/api/v1/integrations/api-football/status", (route) => route.fulfill({ json: { configured: true, calls_used: 2, remaining: 88, selected_team: null, last_run: { public_id: "run-1", status: "queued", stages: [] } } }));
  await page.route("**/api/v1/seasons", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/teams", (route) => route.fulfill({ json: [] }));

  await page.goto("/");
  await page.getByLabel("Nom du club ou espace").fill("StatX Tunis");
  await page.getByLabel("Votre nom").fill("Coach StatX");
  await page.getByLabel("Adresse e-mail").fill("coach@statx.local");
  await page.getByLabel("Mot de passe").fill("A-secure-local-passphrase-2026");
  await page.getByLabel("Votre fonction").selectOption("coach");
  await page.getByRole("button", { name: "Continuer vers le club" }).click();
  const clubButton = page.getByRole("button", { name: "Choisir Espérance ST" });
  await expect(clubButton).toBeVisible();
  expect((await clubButton.boundingBox())?.height).toBeGreaterThanOrEqual(48);
  await clubButton.click();
  await page.getByRole("button", { name: "Vérifier la configuration" }).click();
  await page.getByRole("button", { name: "Créer l’espace et importer" }).click();
  await expect(page.getByRole("heading", { name: "Centre opérationnel StatX" })).toBeVisible();
  expect(setupPayload).toMatchObject({ job_title: "coach", selected_club: { team_provider_id: "1001", league_provider_id: "202" } });
});
