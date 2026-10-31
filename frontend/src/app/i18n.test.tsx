import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PitchInvariant, setDocumentLanguage } from "./i18n";


describe("language direction", () => {
  it("switches the document between French LTR and Arabic RTL", () => {
    setDocumentLanguage("ar");
    expect(document.documentElement).toHaveAttribute("lang", "ar");
    expect(document.documentElement).toHaveAttribute("dir", "rtl");

    setDocumentLanguage("fr");
    expect(document.documentElement).toHaveAttribute("lang", "fr");
    expect(document.documentElement).toHaveAttribute("dir", "ltr");
  });

  it("keeps pitch geometry left-to-right under Arabic UI", () => {
    setDocumentLanguage("ar");
    render(<PitchInvariant aria-label="Terrain tactique" />);
    expect(screen.getByLabelText("Terrain tactique")).toHaveAttribute("dir", "ltr");
  });
});
