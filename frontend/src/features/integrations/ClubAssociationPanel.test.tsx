import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClubAssociationPanel } from "./ClubAssociationPanel";

describe("ClubAssociationPanel", () => {
  it("lets an existing admin associate a Tunisian club", async () => {
    const user = userEvent.setup();
    const selectClub = vi.fn().mockResolvedValue({ public_id: "run-1", status: "queued" });
    render(<ClubAssociationPanel
      loadCatalog={vi.fn().mockResolvedValue({ clubs: [{ provider_id: "1", name: "Club Africain", logo_url: null, league_provider_id: "202", league_name: "Ligue 1", season: 2026 }], stale: false })}
      selectClub={selectClub}
    />);
    await user.click(await screen.findByRole("button", { name: "Choisir Club Africain" }));
    await user.click(screen.getByRole("button", { name: "Associer et importer" }));
    expect(selectClub).toHaveBeenCalledWith(expect.objectContaining({ provider_id: "1" }));
  });
});
