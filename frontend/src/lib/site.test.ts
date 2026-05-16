import { describe, expect, it } from "vitest";
import { PUBLIC_SOURCE_REPO_URL } from "./site";

describe("site constants", () => {
  it("exposes an https GitHub URL for public source linking", () => {
    expect(PUBLIC_SOURCE_REPO_URL).toMatch(/^https:\/\/github\.com\/.+/);
  });
});
