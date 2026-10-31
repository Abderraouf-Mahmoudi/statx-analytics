import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ClubDashboardPage } from "./ClubDashboardPage";

describe("ClubDashboardPage", () => {
  it("creates the season and team required by the roster workflow", async () => {
    const user = userEvent.setup();
    const addSeason = vi.fn().mockResolvedValue(undefined);
    const addTeam = vi.fn().mockResolvedValue(undefined);
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><ClubDashboardPage
      loadData={vi.fn().mockResolvedValue({ teams: [], seasons: [] })}
      addSeason={addSeason}
      addTeam={addTeam}
    /></QueryClientProvider>);
    await screen.findByText("Aucune saison configurée");
    await user.type(screen.getByLabelText("Nom de la saison"), "2026/27");
    await user.click(screen.getByRole("button", { name: "Créer la saison" }));
    expect(addSeason).toHaveBeenCalledWith({ name: "2026/27" });
    await user.type(screen.getByLabelText("Nom de l’équipe"), "U17");
    await user.type(screen.getByLabelText("Catégorie"), "academy");
    await user.click(screen.getByRole("button", { name: "Créer l’équipe" }));
    expect(addTeam).toHaveBeenCalledWith({ name: "U17", category: "academy" });
  });
});
