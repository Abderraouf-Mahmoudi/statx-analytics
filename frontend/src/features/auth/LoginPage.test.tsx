import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";

describe("LoginPage", () => {
  it("shows one generic failure and disables submit while pending", async () => {
    const user = userEvent.setup();
    const login = vi.fn().mockRejectedValue(new Error("Invalid email or password"));
    render(<LoginPage login={login} onComplete={vi.fn()} />);
    await user.type(screen.getByLabelText("Adresse e-mail"), "admin@statx.local");
    await user.type(screen.getByLabelText("Mot de passe"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou mot de passe incorrect");
  });
});
