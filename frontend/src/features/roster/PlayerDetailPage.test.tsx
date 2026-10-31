import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PlayerDetailPage } from "./PlayerDetailPage";

describe("PlayerDetailPage", () => {
  it("records guardian evidence and revokes an active consent", async () => {
    const user = userEvent.setup();
    const addConsent = vi.fn().mockResolvedValue(undefined);
    const revokeConsent = vi.fn().mockResolvedValue(undefined);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><PlayerDetailPage
      playerId="player-1"
      onClose={() => undefined}
      loadDetail={vi.fn().mockResolvedValue({
        player: { public_id: "player-1", first_name: "Amina", last_name: "Ben Salah", birth_date: "2010-11-20" },
        consents: [{ public_id: "consent-1", status: "active", consent_type: "passport_publication", document_sha256: "a".repeat(64), subject_is_minor: true }],
      })}
      addConsent={addConsent}
      revokeConsent={revokeConsent}
    /></QueryClientProvider>);
    await screen.findByRole("heading", { name: "Amina Ben Salah" });
    await user.type(screen.getByLabelText("Empreinte SHA-256"), "b".repeat(64));
    await user.type(screen.getByLabelText("Représentant légal"), "Parent Ben Salah");
    await user.click(screen.getByRole("button", { name: "Enregistrer le consentement" }));
    expect(addConsent).toHaveBeenCalledWith(expect.objectContaining({ guardian_name: "Parent Ben Salah" }));
    await user.click(screen.getByRole("button", { name: "Révoquer" }));
    expect(revokeConsent).toHaveBeenCalledWith("consent-1");
  });
});
