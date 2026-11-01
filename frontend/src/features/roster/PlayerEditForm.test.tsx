import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PlayerEditForm } from "./PlayerEditForm";

describe("PlayerEditForm", () => {
  it("uses a controlled position list and keeps editable profile fields", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<PlayerEditForm player={{
      public_id: "p1", first_name: "Amina", last_name: "Ben Salah", display_name: "Amina Ben Salah",
      primary_position: "CM", secondary_positions: [], preferred_foot: "left",
    }} onSubmit={onSubmit} onCancel={vi.fn()} />);

    expect(screen.getByLabelText("Poste principal")).toHaveRole("combobox");
    await user.selectOptions(screen.getByLabelText("Poste principal"), "AM");
    await user.clear(screen.getByLabelText("Nom d’affichage"));
    await user.click(screen.getByRole("button", { name: "Enregistrer les modifications" }));
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ primary_position: "AM", display_name: null }));
  });
});
