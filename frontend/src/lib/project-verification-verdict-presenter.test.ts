import { describe, expect, it } from "vitest";
import {
  getProjectVerificationVerdictBannerFingerprint,
  projectVerificationVerdictAriaLabelForBand,
} from "./project-verification-verdict-presenter";

describe("project-verification-verdict-presenter", () => {
  it.each([
    [
      "green",
      "border-verdict-green bg-verdict-green-bg border-2 [--verdict-accent:var(--color-verdict-green)]|bg-white/85 text-verdict-green ring-2 ring-verdict-green/30|text-verdict-green",
    ],
    [
      "yellow",
      "border-verdict-yellow bg-verdict-yellow-bg border-2 [--verdict-accent:var(--color-verdict-yellow)]|bg-white/85 text-verdict-yellow ring-2 ring-verdict-yellow/40|text-verdict-yellow",
    ],
    [
      "red",
      "border-verdict-red bg-verdict-red-bg border-2 [--verdict-accent:var(--color-verdict-red)]|bg-white/85 text-verdict-red ring-2 ring-verdict-red/30|text-verdict-red",
    ],
  ] as const)(
    "`%s` palette fingerprint stays stable across icon + headings",
    (verdict, expected) => {
      expect(getProjectVerificationVerdictBannerFingerprint(verdict)).toBe(
        expected,
      );
    },
  );

  it("assigns readable band labels distinct from hue-only signalling", () => {
    expect(projectVerificationVerdictAriaLabelForBand("green")).toContain(
      "verde",
    );
    expect(projectVerificationVerdictAriaLabelForBand("yellow")).toContain(
      "amarilla",
    );
    expect(projectVerificationVerdictAriaLabelForBand("red")).toContain(
      "roja",
    );
  });
});
