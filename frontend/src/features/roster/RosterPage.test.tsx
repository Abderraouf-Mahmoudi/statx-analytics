import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RosterPage } from "./RosterPage";

function renderPage(load = vi.fn().mockResolvedValue([])) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={client}><RosterPage loadRoster={load} /></QueryClientProvider>);
}

describe("RosterPage", () => {
  it("shows loading then an actionable empty state", async () => {
    renderPage();
    expect(screen.getByRole("status")).toHaveTextContent("Chargement");
    expect(await screen.findByText("Aucun joueur inscrit")).toBeVisible();
  });
  it("renders populated roster with textual publication state", async () => {
    renderPage(vi.fn().mockResolvedValue([{ player_id: "p1", first_name: "Amina", last_name: "Ben Salah", shirt_number: 8, position: "CM", publishable: false }]));
    expect(await screen.findByText("Amina Ben Salah")).toBeVisible();
    expect(screen.getByText("Publication bloquée")).toBeVisible();
  });
  it("creates a player identity and its seasonal registration from the touch workflow", async () => {
    const user = userEvent.setup();
    const createRosterEntry = vi.fn().mockResolvedValue(undefined);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><RosterPage
      loadRoster={vi.fn().mockResolvedValue([])}
      loadContext={vi.fn().mockResolvedValue({
        teams: [{ public_id: "11111111-1111-4111-8111-111111111111", name: "U17" }],
        seasons: [{ public_id: "22222222-2222-4222-8222-222222222222", name: "2026/27" }],
      })}
      createRosterEntry={createRosterEntry}
    /></QueryClientProvider>);
    await screen.findByText("Aucun joueur inscrit");
    await user.click(screen.getByRole("button", { name: "Ajouter un joueur" }));
    await user.type(screen.getByLabelText("Prénom"), "Amina");
    await user.type(screen.getByLabelText("Nom"), "Ben Salah");
    await user.type(screen.getByLabelText("Date de naissance"), "2010-11-20");
    await user.type(screen.getByLabelText("Poste principal"), "CM");
    await user.type(screen.getByLabelText("Numéro"), "8");
    await user.click(screen.getByRole("button", { name: "Créer et inscrire" }));
    expect(createRosterEntry).toHaveBeenCalledWith(expect.objectContaining({
      player: expect.objectContaining({ first_name: "Amina", last_name: "Ben Salah" }),
      registration: expect.objectContaining({ shirt_number: 8 }),
    }));
  });
});
