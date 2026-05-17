import { describe, expect, it } from "vitest";
import { legalChunkIncludedBySimilarity } from "./rag-similarity-gate";

describe("rag similarity gate (BVA vs backend retrieval)", () => {
  const nominal = 0.65;

  it("retains citations at exemplar highs (≥ nominal)", () => {
    expect(legalChunkIncludedBySimilarity(0.651, nominal)).toBe(true);
  });

  it("drops citations at exemplar lows (< nominal)", () => {
    expect(legalChunkIncludedBySimilarity(0.649, nominal)).toBe(false);
  });

  it("treats exact nominal as qualifying (boundary on threshold)", () => {
    expect(legalChunkIncludedBySimilarity(nominal, nominal)).toBe(true);
  });
});
