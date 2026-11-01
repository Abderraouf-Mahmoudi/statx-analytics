import { expect, test } from "@playwright/test";

test("tablet roster keeps touch targets and RTL-safe pitch direction", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 768 });
  await page.goto("/");
  await page.getByRole("heading", { name: /Créer votre espace football|Connexion StatX|Centre opérationnel StatX/ }).waitFor();
  if (await page.getByRole("heading", { name: "Créer votre espace football" }).isVisible()) {
    await page.getByLabel("Nom du club ou espace").fill("StatX Touch Club"); await page.getByLabel("Votre nom").fill("Admin");
    await page.getByLabel("Adresse e-mail").fill("admin@statx.local"); await page.getByLabel("Mot de passe").fill("A-secure-local-passphrase-2026");
    await page.getByRole("button", { name: "Continuer vers le club" }).click(); await page.getByRole("button", { name: "Continuer sans import" }).click(); await page.getByRole("button", { name: "Créer l’espace local" }).click();
  }
  if (await page.getByRole("heading", { name: "Connexion StatX" }).isVisible().catch(() => false)) {
    await page.getByLabel("Adresse e-mail").fill("admin@statx.local"); await page.getByLabel("Mot de passe").fill("A-secure-local-passphrase-2026");
    await page.getByRole("button", { name: "Se connecter" }).click();
  }
  await page.getByRole("heading", { name: /Choisir votre club tunisien|Centre opérationnel StatX/ }).waitFor();
  if (await page.getByRole("heading", { name: "Choisir votre club tunisien" }).isVisible().catch(() => false)) {
    await page.getByRole("button", { name: "Continuer sans import" }).click();
  }
  await expect(page.getByRole("heading", { name: "Centre opérationnel StatX" })).toBeVisible();
  await page.getByLabel("Nom de la saison").fill("2026/27");
  await page.getByRole("button", { name: "Créer la saison" }).click();
  await page.getByLabel("Nom de l’équipe").fill("U17");
  await page.getByLabel("Catégorie").fill("academy");
  await page.getByRole("button", { name: "Créer l’équipe" }).click();
  await page.getByRole("link", { name: "Effectif" }).click();
  await expect(page.getByRole("heading", { name: "Effectif" })).toBeVisible();
  const box = await page.getByRole("button", { name: "Ajouter un joueur" }).boundingBox();
  expect(box?.height).toBeGreaterThanOrEqual(48);
  await page.getByRole("button", { name: "Ajouter un joueur" }).click();
  await page.getByLabel("Prénom").fill("Amina");
  await page.getByLabel("Nom", { exact: true }).fill("Ben Salah");
  await page.getByLabel("Date de naissance").fill("2010-11-20");
  await page.getByLabel("Poste principal").selectOption("CM");
  await page.getByLabel("Numéro").fill("8");
  await page.getByRole("button", { name: "Créer et inscrire" }).click();
  await expect(page.getByText("Amina Ben Salah")).toBeVisible();
  const columns = await page.locator(".roster-card-grid").evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(" ").length);
  expect(columns).toBe(3);
  await page.getByRole("button", { name: "Changer de langue" }).click();
  await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
  await expect(page.getByLabel("Repère terrain invariant")).toHaveAttribute("dir", "ltr");
});
