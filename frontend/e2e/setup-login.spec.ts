import { expect, test } from "@playwright/test";

test("first setup, logout, failed login, and successful login", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Configurer votre espace club" })).toBeVisible();
  await page.getByLabel("Nom du club").fill("StatX E2E Club");
  await page.getByLabel("Nom administrateur").fill("Admin StatX");
  await page.getByLabel("Adresse e-mail").fill("admin@statx.local");
  await page.getByLabel("Mot de passe").fill("A-secure-local-passphrase-2026");
  await page.getByRole("button", { name: "Créer l’espace StatX" }).click();
  await page.getByRole("heading", { name: /Choisir votre club tunisien|Centre opérationnel StatX/ }).waitFor();
  if (await page.getByRole("heading", { name: "Choisir votre club tunisien" }).isVisible().catch(() => false)) {
    await page.getByRole("button", { name: "Continuer sans import" }).click();
  }
  await expect(page.getByRole("heading", { name: "Centre opérationnel StatX" })).toBeVisible();

  await page.getByRole("button", { name: "Déconnexion" }).click();
  await expect(page.getByRole("heading", { name: "Connexion StatX" })).toBeVisible();
  await page.getByLabel("Adresse e-mail").fill("admin@statx.local");
  await page.getByLabel("Mot de passe").fill("wrong-password");
  await page.getByRole("button", { name: "Se connecter" }).click();
  if (await page.getByRole("heading", { name: "Choisir votre club tunisien" }).isVisible().catch(() => false)) {
    await page.getByRole("button", { name: "Continuer sans import" }).click();
  }
  await expect(page.getByRole("alert")).toContainText("E-mail ou mot de passe incorrect");
  await page.getByLabel("Mot de passe").fill("A-secure-local-passphrase-2026");
  await page.getByRole("button", { name: "Se connecter" }).click();
  await page.getByRole("heading", { name: /Choisir votre club tunisien|Centre opérationnel StatX/ }).waitFor();
  await expect(page.getByRole("heading", { name: "Centre opérationnel StatX" })).toBeVisible();
});
