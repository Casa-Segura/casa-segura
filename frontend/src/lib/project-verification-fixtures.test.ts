import { describe, expect, it } from "vitest";
import { getProjectVerificationFixture } from "@/lib/project-verification-fixtures";

describe("getProjectVerificationFixture", () => {
  it("maps green yellow red", () => {
    expect(getProjectVerificationFixture("green").verdict).toBe("green");
    expect(getProjectVerificationFixture("yellow").verdict).toBe("yellow");
    expect(getProjectVerificationFixture("red").verdict).toBe("red");
  });

  it("defaults unknown query to yellow band", () => {
    expect(getProjectVerificationFixture("nope").verdict).toBe("yellow");
  });
});
