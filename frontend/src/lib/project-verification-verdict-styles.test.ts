import { describe, expect, it } from "vitest";
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
});
