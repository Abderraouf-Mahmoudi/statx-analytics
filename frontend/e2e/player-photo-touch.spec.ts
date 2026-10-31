import { expect, test } from "@playwright/test";

test("tablet manual player workflow exposes camera and gallery portrait controls", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 1024 });
  await page.goto("/");
  await page.getByRole("heading", { name: /Connexion StatX|Choisir votre club tunisien|Centre opérationnel StatX/ }).waitFor();
  if (await page.getByRole("heading", { name: "Connexion StatX" }).isVisible().catch(() => false)) {
    await page.getByLabel("Adresse e-mail").fill("admin@statx.local");
    await page.getByLabel("Mot de passe").fill("A-secure-local-passphrase-2026");
    await page.getByRole("button", { name: "Se connecter" }).click();
  }
  await page.getByRole("heading", { name: /Choisir votre club tunisien|Centre opérationnel StatX/ }).waitFor();
  if (await page.getByRole("heading", { name: "Choisir votre club tunisien" }).isVisible().catch(() => false)) {
    await page.getByRole("button", { name: "Continuer sans import" }).click();
  }
  await expect(page.getByRole("heading", { name: "Centre opérationnel StatX" })).toBeVisible();
  await page.getByLabel("Nom de la saison").fill("Photo 2026/27");
  await page.getByRole("button", { name: "Créer la saison" }).click();
  await page.getByLabel("Nom de l’équipe").fill("Photo Team");
  await page.getByRole("button", { name: "Créer l’équipe" }).click();
  await page.getByRole("link", { name: "Effectif" }).click();
  await page.getByRole("button", { name: "Ajouter un joueur" }).click();

  const camera = page.getByLabel("Prendre une photo");
  const gallery = page.getByLabel("Choisir dans la galerie");
  await expect(camera).toHaveAttribute("capture", "user");
  await expect(gallery).not.toHaveAttribute("capture", /.+/);
  await gallery.setInputFiles({ name: "portrait.png", mimeType: "image/png", buffer: Buffer.from("portrait-e2e") });
  await expect(page.getByAltText("Aperçu du portrait")).toBeVisible();
  const addBox = await page.getByRole("button", { name: "Créer et inscrire" }).boundingBox();
  expect(addBox?.height).toBeGreaterThanOrEqual(48);
});
