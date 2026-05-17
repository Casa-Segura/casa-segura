import { describe, expect, it, afterEach } from "vitest";
import {
  isProjectVerificationDemoLinksEnabled,
  isProjectVerificationEnabled,
} from "./project-verification-env";

const originalPv = process.env.PROJECT_VERIFICATION_ENABLED;
const originalDemoLinks = process.env.PROJECT_VERIFICATION_DEMO_LINKS;
const originalNodeEnv = process.env.NODE_ENV;

afterEach(() => {
  if (originalPv === undefined) {
    delete process.env.PROJECT_VERIFICATION_ENABLED;
  } else {
    process.env.PROJECT_VERIFICATION_ENABLED = originalPv;
  }

  if (originalDemoLinks === undefined) {
    delete process.env.PROJECT_VERIFICATION_DEMO_LINKS;
  } else {
    process.env.PROJECT_VERIFICATION_DEMO_LINKS = originalDemoLinks;
  }

  process.env.NODE_ENV = originalNodeEnv;
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

  it("treats unknown truthy-ish strings as off (safe rollout)", () => {
    process.env.PROJECT_VERIFICATION_ENABLED = " maybe ";
    expect(isProjectVerificationEnabled()).toBe(false);
    process.env.PROJECT_VERIFICATION_ENABLED = "truthy_but_not_allowlisted";
    expect(isProjectVerificationEnabled()).toBe(false);
  });

  it("ignores leading and trailing whitespace for allowlisted on values", () => {
    process.env.PROJECT_VERIFICATION_ENABLED = "  TRUE  ";
    expect(isProjectVerificationEnabled()).toBe(true);
  });
});

describe("isProjectVerificationDemoLinksEnabled", () => {
  it("defaults to true in development", () => {
    process.env.NODE_ENV = "development";
    delete process.env.PROJECT_VERIFICATION_DEMO_LINKS;
    expect(isProjectVerificationDemoLinksEnabled()).toBe(true);
  });

  it("defaults to off in production unless explicitly enabled", () => {
    process.env.NODE_ENV = "production";
    delete process.env.PROJECT_VERIFICATION_DEMO_LINKS;
    expect(isProjectVerificationDemoLinksEnabled()).toBe(false);

    process.env.PROJECT_VERIFICATION_DEMO_LINKS = "TRUE";
    expect(isProjectVerificationDemoLinksEnabled()).toBe(true);

    delete process.env.PROJECT_VERIFICATION_DEMO_LINKS;
    process.env.PROJECT_VERIFICATION_DEMO_LINKS = "0";
    expect(isProjectVerificationDemoLinksEnabled()).toBe(false);
  });
});
