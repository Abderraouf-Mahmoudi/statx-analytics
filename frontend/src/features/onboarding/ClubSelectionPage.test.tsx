import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ClubSelectionPage } from "./ClubSelectionPage";

const clubs = [
  { provider_id: "1001", name: "Espérance ST", logo_url: "https://media.api-sports.io/football/teams/1001.png", league_provider_id: "202", league_name: "Ligue 1", season: 2026 },
  { provider_id: "1002", name: "Club Africain", logo_url: null, league_provider_id: "202", league_name: "Ligue 1", season: 2026 },
];

describe("ClubSelectionPage", () => {
  it("searches cached clubs and completes the selected club sync", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    const selectClub = vi.fn().mockResolvedValue({ public_id: "run-1", status: "queued" });
    render(<ClubSelectionPage
      configured
      loadClubs={vi.fn().mockResolvedValue({ clubs, stale: false })}
      selectClub={selectClub}
      waitForSync={vi.fn().mockResolvedValue({ public_id: "run-1", status: "completed", result_summary: { teams: 2, players: 28, fixtures: 12, standings: 1, absent: 0 } })}
      onComplete={onComplete}
    />);

    expect(await screen.findByText("Espérance ST")).toBeVisible();
    await user.type(screen.getByRole("searchbox", { name: "Rechercher un club" }), "Espérance");
    expect(screen.queryByText("Club Africain")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Choisir Espérance ST" }));
    await user.click(screen.getByRole("button", { name: "Confirmer et importer" }));

    expect(await screen.findByText("28 joueurs importés")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Ouvrir StatX" }));
    expect(onComplete).toHaveBeenCalledOnce();
    expect(selectClub).toHaveBeenCalledWith(expect.objectContaining({ provider_id: "1001" }));
  });

  it("keeps manual onboarding available when integration is disabled", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<ClubSelectionPage configured={false} onComplete={onComplete} />);
    expect(screen.getByText("API-Football n’est pas configurée")).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Continuer sans import" }));
    expect(onComplete).toHaveBeenCalledOnce();
  });
});
