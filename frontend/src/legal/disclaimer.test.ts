import { describe, expect, it } from "vitest";
import { DISCLAIMER_ID, DISCLAIMER_SHORT } from "./disclaimer";

describe("disclaimer", () => {
  it("preserves BR-07 literal (including í)", () => {
    expect(DISCLAIMER_SHORT).toBe(`Esto no es asesor\u00EDa legal`);
  });

  it("exposes stable disclaimer id for future i18n", () => {
    expect(DISCLAIMER_ID.length).toBeGreaterThan(0);
    expect(DISCLAIMER_ID).toMatch(/^[\w.]+$/);
  });
});
