import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";

describe("project verification deployment gate docs", () => {
  it("documents the behavioural matrix beside code", () => {
    const docPath = path.join(
      process.cwd(),
      "..",
      "docs",
      "guides",
      "project-verification-fe-be-gates.md",
    );
    expect(existsSync(docPath)).toBe(true);
    const text = readFileSync(docPath, "utf8");
    expect(text).toContain("| Frontend gate | Backend gate |");
    expect(text).toContain("`PROJECT_VERIFICATION_ENABLED`");
  });
});
