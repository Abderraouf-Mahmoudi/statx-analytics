import { describe, expect, it } from "vitest";
import { setupSchema } from "./setupSchema";

const validSetup = {
  organization_name: "Espérance StatX",
  admin_display_name: "Admin StatX",
  email: "admin@statx.local",
  password: "A-secure-local-passphrase-2026",
  country_code: "TN",
  default_locale: "fr" as const,
  timezone: "Africa/Tunis",
};

describe("setupSchema", () => {
  it("requires a supported football function", () => {
    expect(setupSchema.safeParse(validSetup).success).toBe(false);
    expect(setupSchema.parse({ ...validSetup, job_title: "coach" }).job_title).toBe("coach");
    expect(setupSchema.safeParse({ ...validSetup, job_title: "president" }).success).toBe(false);
  });
});
