import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  reportProjectVerificationTelemetry,
  type ProjectVerificationTelemetryPayload,
} from "./project-verification-telemetry";

describe("project-verification-telemetry", () => {
  const originalLog = process.env.PROJECT_VERIFICATION_TELEMETRY_LOG;

  beforeEach(() => {
    vi.spyOn(console, "info").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    if (originalLog === undefined) {
      delete process.env.PROJECT_VERIFICATION_TELEMETRY_LOG;
    } else {
      process.env.PROJECT_VERIFICATION_TELEMETRY_LOG = originalLog;
    }
  });

  it("noop when telemetry env flag absent", () => {
    delete process.env.PROJECT_VERIFICATION_TELEMETRY_LOG;
    reportProjectVerificationTelemetry({
      event: "project_verification_manual_entry",
      fallback: "manual_form",
      source: "photo_skip",
    });
    expect(console.info).not.toHaveBeenCalled();
  });

  it("logs JSON-safe payload without user fields when enabled", () => {
    process.env.PROJECT_VERIFICATION_TELEMETRY_LOG = "true";
    const payload: ProjectVerificationTelemetryPayload = {
      event: "project_verification_manual_entry",
      fallback: "manual_form",
      source: "photo_skip",
    };
    reportProjectVerificationTelemetry(payload);
    expect(console.info).toHaveBeenCalledTimes(1);
    const [, line] = vi.mocked(console.info).mock.calls[0] as unknown as [
      string,
      string,
    ];
    expect(JSON.parse(line)).toMatchObject({
      event: "project_verification_manual_entry",
      fallback: "manual_form",
      source: "photo_skip",
    });
    expect(JSON.parse(line).address).toBeUndefined();
    expect(JSON.parse(line).developer).toBeUndefined();
  });

  it("logs contract CTA impression without PII-ish keys when enabled", () => {
    process.env.PROJECT_VERIFICATION_TELEMETRY_LOG = "true";
    reportProjectVerificationTelemetry({
      event: "project_verification_contract_cta_impression",
      route: "/verificacion-proyecto/resultado",
    });
    expect(console.info).toHaveBeenCalledTimes(1);
    const [, line] = vi.mocked(console.info).mock.calls[0] as unknown as [
      string,
      string,
    ];
    expect(JSON.parse(line)).toMatchObject({
      event: "project_verification_contract_cta_impression",
      route: "/verificacion-proyecto/resultado",
    });
    expect(JSON.parse(line).developer).toBeUndefined();
  });
});