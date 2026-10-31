import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PlayerCard } from "./PlayerCard";

describe("PlayerCard", () => {
  it("shows identity, provenance, rights and an accessible management action", () => {
    render(<PlayerCard player={{
      player_id: "p1", first_name: "Amina", last_name: "Ben Salah", shirt_number: 8,
      position: "CM", preferred_foot: "left", publishable: false, source: "api_football",
      provider_absent: false, photo_status: "ready", photo_rights_status: "provider_identification_only",
    }} onManage={vi.fn()} />);

    expect(screen.getByText("Amina Ben Salah")).toBeVisible();
    expect(screen.getByText("#8")).toBeVisible();
    expect(screen.getByText("API-Football")).toBeVisible();
    expect(screen.getByText("Identification uniquement")).toBeVisible();
    expect(screen.getByText("Publication bloquée")).toBeVisible();
    expect(screen.getByRole("img", { name: "Portrait de Amina Ben Salah" })).toHaveAttribute("src", expect.stringContaining("/players/p1/photo"));
    expect(screen.getByRole("button", { name: "Gérer Amina Ben Salah" })).toBeVisible();
  });
});
