import { describe, expect, it } from "vitest";
import {
  MANUAL_VERIFICATION_ROUTE,
  buildManualVerificationHandoffPath,
  clampHandoffField,
  impliesOcrRecoverySource,
  parseManualVerificationHandoffSearchParams,
  parseManualHandoffSource,
} from "./project-verification-manual-handoff";

describe("project-verification-manual-handoff", () => {
  it("builds empty path without query when no fields", () => {
    expect(buildManualVerificationHandoffPath({})).toBe(
      MANUAL_VERIFICATION_ROUTE,
    );
  });

  it("encodes prefills and source deterministically", () => {
    const path = buildManualVerificationHandoffPath({
      developer: "  ACME  ",
      project: "Torre norte",
      source: "photo_skip",
    });
    expect(path).toContain("developer=ACME");
    expect(path).toContain("project=Torre+norte");
    expect(path).toContain("source=photo_skip");
  });

  it("clips long fields", () => {
    const long = "a".repeat(300);
    expect(clampHandoffField(long)?.length).toBe(240);
  });

  it("parses multi-value arrays by first entry only", () => {
    const p = parseManualVerificationHandoffSearchParams({
      developer: ["first", "second"],
      source: ["photo_skip"],
    });
    expect(p.initialValues.developer).toBe("first");
    expect(p.source).toBe("photo_skip");
    expect(p.hasPrefill).toBe(true);
  });

  it("rejects unknown source tokens", () => {
    expect(parseManualHandoffSource("evil")).toBeUndefined();
    expect(
      parseManualVerificationHandoffSearchParams({
        source: "not_valid",
      }).source,
    ).toBeUndefined();
  });

  it("implies OCR recovery for future OCR enums only", () => {
    expect(impliesOcrRecoverySource(undefined)).toBe(false);
    expect(impliesOcrRecoverySource("photo_skip")).toBe(false);
    expect(impliesOcrRecoverySource("ocr_failure")).toBe(true);
  });
});
