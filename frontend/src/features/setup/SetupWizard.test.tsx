import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SetupWizard } from "./SetupWizard";

const club = {
  provider_id: "1001",
  name: "Espérance ST",
  logo_url: null,
  league_provider_id: "202",
  league_name: "Ligue 1",
  season: 2026,
};

describe("SetupWizard", () => {
  it("submits function, account and selected club without exposing provider ids", async () => {
    const user = userEvent.setup();
    const bootstrap = vi.fn().mockResolvedValue({ organization_id: "org-1", role: "admin" });
    render(<SetupWizard
      loadCatalog={vi.fn().mockResolvedValue({ clubs: [club], stale: false, quota: { calls_used: 2, remaining: 88 } })}
      bootstrap={bootstrap}
      onComplete={vi.fn()}
    />);

    await user.type(screen.getByLabelText("Nom du club ou espace"), "StatX Tunis");
    await user.type(screen.getByLabelText("Votre nom"), "Coach StatX");
    await user.type(screen.getByLabelText("Adresse e-mail"), "coach@statx.local");
    await user.type(screen.getByLabelText("Mot de passe"), "A-secure-local-passphrase-2026");
    await user.selectOptions(screen.getByLabelText("Votre fonction"), "coach");
    await user.click(screen.getByRole("button", { name: "Continuer vers le club" }));

    expect(await screen.findByRole("button", { name: "Choisir Espérance ST" })).toBeVisible();
    expect(screen.queryByText(/Données historiques/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/provider/i)).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choisir Espérance ST" }));
    await user.click(screen.getByRole("button", { name: "Vérifier la configuration" }));
    expect(screen.getByText("Coach StatX")).toBeVisible();
    expect(screen.getByText("Espérance ST")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Créer l’espace et importer" }));

    expect(bootstrap).toHaveBeenCalledWith(expect.objectContaining({
      job_title: "coach",
      selected_club: expect.objectContaining({ team_provider_id: "1001", league_provider_id: "202" }),
    }));
  });

  it("labels the historical catalog and submits its actual season", async () => {
    const user = userEvent.setup();
    const bootstrap = vi.fn().mockResolvedValue({ organization_id: "org-1", role: "admin" });
    const historicalClub = { ...club, season: 2024 };
    render(<SetupWizard
      loadCatalog={vi.fn().mockResolvedValue({
        clubs: [historicalClub],
        stale: false,
        historical_fallback: true,
        historical_season: 2024,
        quota: { calls_used: 6, remaining: 94 },
      })}
      bootstrap={bootstrap}
      onComplete={vi.fn()}
    />);

    await user.type(screen.getByLabelText("Nom du club ou espace"), "StatX Tunis");
    await user.type(screen.getByLabelText("Votre nom"), "Coach StatX");
    await user.type(screen.getByLabelText("Adresse e-mail"), "coach@statx.local");
    await user.type(screen.getByLabelText("Mot de passe"), "A-secure-local-passphrase-2026");
    await user.click(screen.getByRole("button", { name: "Continuer vers le club" }));

    expect(await screen.findByText("Données historiques — saison 2024")).toBeVisible();
    expect(screen.getByText("Ligue 1 · 2024")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Choisir Espérance ST" }));
    await user.click(screen.getByRole("button", { name: "Vérifier la configuration" }));
    await user.click(screen.getByRole("button", { name: "Créer l’espace et importer" }));

    expect(bootstrap).toHaveBeenCalledWith(expect.objectContaining({
      selected_club: expect.objectContaining({ season: 2024 }),
    }));
  });

  it("supports a manual setup fallback", async () => {
    const user = userEvent.setup();
    const bootstrap = vi.fn().mockResolvedValue({ organization_id: "org-1", role: "admin" });
    render(<SetupWizard loadCatalog={vi.fn().mockRejectedValue(new Error("offline"))} bootstrap={bootstrap} onComplete={vi.fn()} />);
    await user.type(screen.getByLabelText("Nom du club ou espace"), "Club local");
    await user.type(screen.getByLabelText("Votre nom"), "Directeur Local");
    await user.type(screen.getByLabelText("Adresse e-mail"), "admin@local.test");
    await user.type(screen.getByLabelText("Mot de passe"), "A-secure-local-passphrase-2026");
    await user.click(screen.getByRole("button", { name: "Continuer vers le club" }));
    await user.click(await screen.findByRole("button", { name: "Continuer sans import" }));
    await user.click(screen.getByRole("button", { name: "Créer l’espace local" }));
    expect(bootstrap).toHaveBeenCalledWith(expect.not.objectContaining({ selected_club: expect.anything() }));
  });
});
