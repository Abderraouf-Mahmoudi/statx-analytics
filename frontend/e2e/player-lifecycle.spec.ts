import { expect, test } from "@playwright/test";

test("tablet coach edits and deactivates an imported player", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.route("**/api/v1/setup/status", (route) => route.fulfill({ json: { required: false } }));
  await page.route("**/api/v1/session", (route) => route.fulfill({ json: { user_id: "u1", organization_id: "o1", display_name: "Coach", email: "coach@statx.local", role: "coach", job_title: "coach", locale: "fr" } }));
  await page.route("**/api/v1/integrations/api-football/status", (route) => route.fulfill({ json: { configured: true, calls_used: 8, remaining: 82, selected_team: { public_id: "t1", name: "Espérance ST" }, last_run: null } }));
  await page.route("**/api/v1/teams", (route) => route.fulfill({ json: [{ public_id: "t1", name: "Espérance ST" }] }));
  await page.route("**/api/v1/seasons", (route) => route.fulfill({ json: [{ public_id: "s1", name: "Ligue 1 2026" }] }));
  await page.route("**/api/v1/teams/t1/roster?season_id=s1", (route) => route.fulfill({ json: [{ registration_id: "r1", player_id: "p1", first_name: "Amina", last_name: "Ben Salah", shirt_number: 8, position: "CM", publishable: true, source: "api_football", photo_status: "no_photo", registration_status: "active" }] }));
  await page.route("**/api/v1/players/p1/consents", (route) => route.fulfill({ json: [] }));
  await page.route("**/api/v1/players/p1/photo/status", (route) => route.fulfill({ json: { public_id: null, source: null, status: "no_photo" } }));
  await page.route("**/api/v1/players/p1", async (route) => route.request().method() === "PATCH" ? route.fulfill({ json: { public_id: "p1", first_name: "Amina", last_name: "Ben Salah", display_name: null, primary_position: "AM", secondary_positions: [], preferred_foot: "left" } }) : route.fulfill({ json: { public_id: "p1", first_name: "Amina", last_name: "Ben Salah", display_name: "Amina Ben Salah", primary_position: "CM", secondary_positions: [], preferred_foot: "left" } }));
  let deactivated = false;
  await page.route("**/api/v1/registrations/r1/deactivate", (route) => { deactivated = true; return route.fulfill({ json: { public_id: "r1", status: "inactive" } }); });

  await page.goto("/roster");
  await page.getByRole("button", { name: "Gérer Amina Ben Salah" }).click();
  await page.getByRole("button", { name: "Modifier" }).click();
  await page.getByLabel("Poste principal").selectOption("AM");
  await page.getByRole("button", { name: "Enregistrer les modifications" }).click();
  await page.getByRole("button", { name: "Retirer de l’effectif" }).click();
  await expect.poll(() => deactivated).toBe(true);
});
