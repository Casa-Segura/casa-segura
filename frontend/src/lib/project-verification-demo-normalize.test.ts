import { describe, expect, it } from "vitest";
import { normalizeProjectVerificationDemoResult } from "./project-verification-demo-normalize";

describe("normalizeProjectVerificationDemoResult", () => {
  it("maps snake_case data_freshness_note", () => {
    const r = normalizeProjectVerificationDemoResult({
      verdict: "green",
      headline: "H",
      rationale: ["a", "b"],
      data_freshness_note: "Nota fresca",
      stub: true,
    });
    expect(r).toEqual({
      verdict: "green",
      headline: "H",
      rationale: ["a", "b"],
      dataFreshnessNote: "Nota fresca",
    });
  });

  it("accepts camelCase dataFreshnessNote", () => {
    const r = normalizeProjectVerificationDemoResult({
      verdict: "yellow",
      headline: "H2",
      rationale: [],
      dataFreshnessNote: "X",
    });
    expect(r?.dataFreshnessNote).toBe("X");
  });

  it("returns null for invalid verdict", () => {
    expect(
      normalizeProjectVerificationDemoResult({
        verdict: "blue",
        headline: "H",
        rationale: [],
      }),
    ).toBeNull();
  });

  it("returns null when headline missing", () => {
    expect(
      normalizeProjectVerificationDemoResult({
        verdict: "red",
        rationale: [],
      }),
    ).toBeNull();
  });
});
