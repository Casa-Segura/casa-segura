import { describe, expect, it } from "vitest";
import {
  getProjectVerificationVerdictBannerFingerprint,
  projectVerificationVerdictAriaLabelForBand,
} from "@/lib/project-verification-verdict-presenter";
import { verdictVisualTone } from "@/lib/project-verification-verdict-styles";

describe("project-verification verdict visual tokens", () => {
  it.each(["green", "yellow", "red"] as const)(
    "defines distinct palettes for `%s`",
    (v) => {
      const tone = verdictVisualTone(v);
      expect(tone.container.length).toBeGreaterThan(16);
      expect(tone.iconRing.length).toBeGreaterThan(16);
      expect(tone.title).toContain(v === "yellow" ? "yellow" : v);
    },
  );

  it("isolates palettes between opposing bands", () => {
    expect(verdictVisualTone("green").container).not.toEqual(
      verdictVisualTone("red").container,
    );
    expect(verdictVisualTone("green").iconRing).not.toEqual(
      verdictVisualTone("yellow").iconRing,
    );
  });

  it("SSR banner fingerprints stay distinct across bands", () => {
    const fingers = (["green", "yellow", "red"] as const).map((v) =>
      getProjectVerificationVerdictBannerFingerprint(v),
    );
    expect(new Set(fingers).size).toBe(3);
  });

  it("uses distinct accessibility labels per band", () => {
    const aria = (["green", "yellow", "red"] as const).map(
      projectVerificationVerdictAriaLabelForBand,
    );
    expect(new Set(aria).size).toBe(3);
  });
});
