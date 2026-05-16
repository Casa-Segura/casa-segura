import { describe, expect, it, afterEach } from "vitest";
import { isProjectVerificationEnabled } from "./project-verification-env";

const original = process.env.PROJECT_VERIFICATION_ENABLED;

afterEach(() => {
  if (original === undefined) {
    delete process.env.PROJECT_VERIFICATION_ENABLED;
  } else {
    process.env.PROJECT_VERIFICATION_ENABLED = original;
  }
});

describe("isProjectVerificationEnabled", () => {
  it("is false when unset", () => {
    delete process.env.PROJECT_VERIFICATION_ENABLED;
    expect(isProjectVerificationEnabled()).toBe(false);
  });

  it("is false for typical off strings", () => {
    process.env.PROJECT_VERIFICATION_ENABLED = "false";
    expect(isProjectVerificationEnabled()).toBe(false);
    process.env.PROJECT_VERIFICATION_ENABLED = "0";
    expect(isProjectVerificationEnabled()).toBe(false);
  });

  it("is true for canonical on values", () => {
    process.env.PROJECT_VERIFICATION_ENABLED = "true";
    expect(isProjectVerificationEnabled()).toBe(true);
    process.env.PROJECT_VERIFICATION_ENABLED = "TRUE";
    expect(isProjectVerificationEnabled()).toBe(true);
    process.env.PROJECT_VERIFICATION_ENABLED = "1";
    expect(isProjectVerificationEnabled()).toBe(true);
    process.env.PROJECT_VERIFICATION_ENABLED = "yes";
    expect(isProjectVerificationEnabled()).toBe(true);
  });
});
