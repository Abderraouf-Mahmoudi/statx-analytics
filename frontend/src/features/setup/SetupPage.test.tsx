import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SetupPage } from "./SetupPage";

describe("SetupPage", () => {
  it("validates password rules and completes bootstrap", async () => {
    const user = userEvent.setup();
    const submit = vi.fn().mockResolvedValue({ role: "admin" });
    render(<SetupPage bootstrap={submit} onComplete={vi.fn()} />);
    await user.type(screen.getByLabelText("Nom du club ou espace"), "StatX Club");
    await user.type(screen.getByLabelText("Votre nom"), "Admin StatX");
    await user.type(screen.getByLabelText("Adresse e-mail"), "admin@statx.local");
    await user.type(screen.getByLabelText("Mot de passe"), "court");
    await user.click(screen.getByRole("button", { name: "Continuer vers le club" }));
    expect(await screen.findByText(/12 caractères/)).toBeVisible();
    expect(submit).not.toHaveBeenCalled();
  });
});
