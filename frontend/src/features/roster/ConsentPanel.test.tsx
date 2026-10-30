import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConsentPanel } from "./ConsentPanel";

describe("ConsentPanel", () => {
  it("explains a missing minor consent with text and icon", () => {
    render(<ConsentPanel isMinor consents={[]} />);
    expect(screen.getByText("Consentement du représentant requis")).toBeVisible();
    expect(screen.getByLabelText("Avertissement")).toBeVisible();
  });
  it("marks revoked evidence as non-publishable", () => {
    render(<ConsentPanel isMinor consents={[{ public_id: "c1", status: "revoked", document_sha256: "a".repeat(64), revoked_at: "2026-10-30" }]} />);
    expect(screen.getByText("Révoqué")).toBeVisible();
    expect(screen.getByText("Publication bloquée")).toBeVisible();
  });
});
