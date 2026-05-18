import { describe, expect, it } from "vitest";
import {
  BRAND_LOGO_PATH,
  PUBLIC_SOURCE_REPO_URL,
  PUBLIC_TEST_DATA_DRIVE_URL,
} from "./site";

describe("site constants", () => {
  it("exposes an https GitHub URL for public source linking", () => {
    expect(PUBLIC_SOURCE_REPO_URL).toMatch(/^https:\/\/github\.com\/.+/);
    expect(PUBLIC_SOURCE_REPO_URL).toContain("Casa-Segura/casa-segura");
  });

  it("exposes an https Google Drive URL for shared test fixtures", () => {
    expect(PUBLIC_TEST_DATA_DRIVE_URL).toMatch(
      /^https:\/\/drive\.google\.com\/drive\/folders\//,
    );
  });

  it("exposes a public brand logo path under /brand", () => {
    expect(BRAND_LOGO_PATH).toBe("/brand/casa-segura-logo.png");
  });
});
