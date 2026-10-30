import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { AppShell } from "./AppShell";


describe("AppShell", () => {
  it("presents the official brand and approved product navigation", () => {
    render(
      <MemoryRouter>
        <AppShell layout="desktop"><div>Workspace</div></AppShell>
      </MemoryRouter>,
    );

    expect(screen.getByAltText("Stat X — Football Data Lab")).toBeVisible();
    const navigation = screen.getByRole("navigation", { name: "Navigation principale" });
    const links = within(navigation).getAllByRole("link");
    expect(links.map((link) => link.textContent?.trim())).toEqual([
      "Accueil",
      "Effectif",
      "Match Center",
      "Analyses",
      "Passeports",
      "Imports",
      "Administration",
    ]);
    expect(navigation).not.toHaveTextContent(/tracking/i);
    links.forEach((link) => expect(link).toHaveClass("touch-target"));
  });

  it("keeps local runtime state visible", () => {
    render(
      <MemoryRouter>
        <AppShell layout="tablet-landscape"><div>Workspace</div></AppShell>
      </MemoryRouter>,
    );
    expect(screen.getAllByText("Poste local actif").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Données locales").length).toBeGreaterThan(0);
  });
});

