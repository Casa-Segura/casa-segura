import { describe, expect, it } from "vitest";
import { verdictVisualTone } from "./project-verification-verdict-styles";

describe("verdictVisualTone", () => {
  it("maps green/yellow/red to stable tonal class bundles", () => {
    expect(verdictVisualTone("green").container).toMatch(/verdict-green/);
    expect(verdictVisualTone("yellow").title).toMatch(/verdict-yellow/);
    expect(verdictVisualTone("red").iconRing).toMatch(/verdict-red/);
  });
});
