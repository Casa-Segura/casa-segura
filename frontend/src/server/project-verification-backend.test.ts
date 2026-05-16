import { afterEach, describe, expect, it, vi } from "vitest";
import {
  fetchProjectVerificationDemoResult,
  mapBillboardUploadPostFailure,
  mapManualVerificationPostFailure,
  postProjectVerificationBillboardUpload,
  postProjectVerificationManual,
} from "./project-verification-backend";

const originalBase = process.env.CASASEGURA_API_BASE_URL;

afterEach(() => {
  vi.unstubAllGlobals();
  if (originalBase === undefined) {
    delete process.env.CASASEGURA_API_BASE_URL;
  } else {
    process.env.CASASEGURA_API_BASE_URL = originalBase;
  }
});

describe("postProjectVerificationManual", () => {
  it("returns configuration when base URL unset", async () => {
    delete process.env.CASASEGURA_API_BASE_URL;
    const r = await postProjectVerificationManual({
      developer: "a",
      project: "b",
      permit: "c",
      address: "d",
    });
    expect(r.ok).toBe(false);
    if (!r.ok) {
      const m = mapManualVerificationPostFailure(r);
      expect(m.uiMessage).toMatch(/CASASEGURA_API_BASE_URL/);
    }
  });

  it("POSTs JSON and parses 201 stub", async () => {
    process.env.CASASEGURA_API_BASE_URL = "http://example.test";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      clone: () => ({
        json: () =>
          Promise.resolve({
            reference_id: "pv-manual-1",
            echo: {
              developer: "Dev",
              project: "Proj",
              permit: "P1",
              address: "Addr",
            },
            detail: "Sin filas",
            stub: true,
          }),
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const r = await postProjectVerificationManual({
      developer: "Dev",
      project: "Proj",
      permit: "P1",
      address: "Addr",
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.referenceId).toBe("pv-manual-1");
      expect(r.echo.project).toBe("Proj");
    }
    expect(fetchMock).toHaveBeenCalledWith(
      "http://example.test/api/v1/project-verification/manual/",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
        }) as Record<string, string>,
      }),
    );
    const [, init] = fetchMock.mock.calls[0]!;
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body).toEqual({
      developer: "Dev",
      project: "Proj",
      permit: "P1",
      address: "Addr",
    });
  });
});

describe("postProjectVerificationBillboardUpload", () => {
  it("returns configuration when base URL unset", async () => {
    delete process.env.CASASEGURA_API_BASE_URL;
    const r = await postProjectVerificationBillboardUpload(
      new File(["x"], "valla.jpg", { type: "image/jpeg" }),
    );
    expect(r.ok).toBe(false);
    if (!r.ok) {
      const m = mapBillboardUploadPostFailure(r);
      expect(m.uiMessage).toMatch(/CASASEGURA_API_BASE_URL/);
    }
  });

  it("POSTs multipart and parses 202 stub", async () => {
    process.env.CASASEGURA_API_BASE_URL = "http://example.test";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 202,
      clone: () => ({
        json: () =>
          Promise.resolve({
            status: "stub_accepted",
            detail: "Imagen recibida",
            stub: true,
          }),
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const r = await postProjectVerificationBillboardUpload(
      new File(["x"], "valla.jpg", { type: "image/jpeg" }),
    );
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.detail).toBe("Imagen recibida");
      expect(r.stub).toBe(true);
    }
    expect(fetchMock).toHaveBeenCalledWith(
      "http://example.test/api/v1/project-verification/billboard-upload/",
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Accept: "application/json",
        }) as Record<string, string>,
      }),
    );
    const [, init] = fetchMock.mock.calls[0]!;
    expect((init as RequestInit).body).toBeInstanceOf(FormData);
  });
});

describe("fetchProjectVerificationDemoResult", () => {
  it("returns null when base unset", async () => {
    delete process.env.CASASEGURA_API_BASE_URL;
    expect(await fetchProjectVerificationDemoResult("green")).toBeNull();
  });

  it("normalizes GET payload", async () => {
    process.env.CASASEGURA_API_BASE_URL = "http://example.test";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            verdict: "red",
            headline: "H",
            rationale: ["r"],
            data_freshness_note: "N",
          }),
      }),
    );
    const out = await fetchProjectVerificationDemoResult("red");
    expect(out).toEqual({
      verdict: "red",
      headline: "H",
      rationale: ["r"],
      dataFreshnessNote: "N",
    });
  });
});

describe("mapManualVerificationPostFailure", () => {
  it("maps project_verification_disabled", () => {
    const m = mapManualVerificationPostFailure({
      ok: false,
      status: 403,
      body: { error_code: "project_verification_disabled" },
    });
    expect(m.uiMessage).toMatch(/no está disponible/i);
  });
});

describe("mapBillboardUploadPostFailure", () => {
  it("maps project_verification_disabled", () => {
    const m = mapBillboardUploadPostFailure({
      ok: false,
      status: 403,
      body: { error_code: "project_verification_disabled" },
    });
    expect(m.uiMessage).toMatch(/no está disponible/i);
  });
});
