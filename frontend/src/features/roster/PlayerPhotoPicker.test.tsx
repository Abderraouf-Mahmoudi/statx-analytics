import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { PlayerPhotoPicker } from "./PlayerPhotoPicker";

describe("PlayerPhotoPicker", () => {
  beforeEach(() => {
    vi.stubGlobal("URL", { createObjectURL: vi.fn(() => "blob:preview"), revokeObjectURL: vi.fn() });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("offers distinct camera and gallery inputs and uploads the selected portrait", async () => {
    const user = userEvent.setup();
    const upload = vi.fn().mockResolvedValue({ public_id: "photo-1", status: "pending" });
    render(<PlayerPhotoPicker playerId="p1" upload={upload} />);

    const camera = screen.getByLabelText("Prendre une photo");
    const gallery = screen.getByLabelText("Choisir dans la galerie");
    expect(camera).toHaveAttribute("accept", "image/*");
    expect(camera).toHaveAttribute("capture", "user");
    expect(gallery).toHaveAttribute("accept", "image/jpeg,image/png,image/webp");
    expect(gallery).not.toHaveAttribute("capture");

    const file = new File(["portrait"], "amina.png", { type: "image/png" });
    await user.upload(gallery, file);
    expect(screen.getByAltText("Aperçu du portrait")).toHaveAttribute("src", "blob:preview");
    await user.click(screen.getByRole("button", { name: "Envoyer le portrait" }));
    expect(upload).toHaveBeenCalledWith("p1", "gallery", file);
    expect(await screen.findByText("Portrait en traitement")).toBeVisible();
  });
});
