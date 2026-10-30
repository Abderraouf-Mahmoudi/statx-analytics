import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
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
});
