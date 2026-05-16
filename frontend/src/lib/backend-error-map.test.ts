import { describe, expect, it } from "vitest";
import { mapBackendError } from "./backend-error-map";

describe("mapBackendError", () => {
  it("maps DISCLAIMER_REQUIRED upper codes", () => {
    const m = mapBackendError({ error_code: "DISCLAIMER_REQUIRED" }, 400);
    expect(m.category).toBe("disclaimer");
    expect(m.uiMessage).toMatch(/aviso legal/);
  });
  it("maps namespaced ingestion codes by tail segment", () => {
    const m = mapBackendError({ error_code: "ingestion.FILE_TOO_LARGE" }, 400);
    expect(m.category).toBe("business");
    expect(m.uiMessage).toMatch(/15 MB/i);
  });
  it("treats 5xx as server", () => {
    const m = mapBackendError({}, 502);
    expect(m.category).toBe("server");
  });
  it("treats status 0 as network", () => {
    const m = mapBackendError({}, 0);
    expect(m.category).toBe("network");
  });
  it("maps project_verification_disabled on 403", () => {
    const m = mapBackendError(
      { error_code: "project_verification_disabled" },
      403,
    );
    expect(m.category).toBe("business");
    expect(m.uiMessage).toMatch(/verificación de proyecto/i);
  });
});
