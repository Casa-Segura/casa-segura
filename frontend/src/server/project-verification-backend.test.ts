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

  it("POSTs JSON and parses 201 evaluation payload", async () => {
    process.env.CASASEGURA_API_BASE_URL = "http://example.test";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      clone: () => ({
        json: () =>
          Promise.resolve({
            reference_id: "pv-manual-1",
            verdict: "yellow",
            headline_key: "pv.headline.yellow",
            rationale_keys: ["pv.reputation.skipped_disabled"],
            heuristic_score: 6.25,
            data_freshness_note_key: "pv.freshness.demo",
            echo: {
              developer: "Dev",
              project: "Proj",
              permit: "P1",
              address: "Addr",
            },
            detail: "OK",
          }),
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const r = await postProjectVerificationManual({
      developer: "Dev",
      project: "Proj",
      permit: "P1",
      address: "Addr",
      submission_source: "billboard_ocr",
      ocr_quality: "medium",
    });
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.referenceId).toBe("pv-manual-1");
      expect(r.echo.project).toBe("Proj");
      expect(r.verdict).toBe("yellow");
      expect(r.headlineKey).toBe("pv.headline.yellow");
      expect(r.rationaleKeys).toContain("pv.reputation.skipped_disabled");
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
    expect(body).toMatchObject({
      developer: "Dev",
      project: "Proj",
      permit: "P1",
      address: "Addr",
      submission_source: "billboard_ocr",
      ocr_quality: "medium",
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

  it("POSTs multipart and parses 200 vision payload", async () => {
    process.env.CASASEGURA_API_BASE_URL = "http://example.test";
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      clone: () => ({
        json: () =>
          Promise.resolve({
            ocr_status: "success",
            fields: {
              developer: "Dev",
              project: "Proj",
              permit: "P1",
              address: "Addr",
            },
            ocr_high_confidence: true,
            ocr_medium_confidence: false,
            ocr_low_confidence: false,
            ocr_quality_hint: "high",
            manual_prefill: {},
            detail: "OK",
          }),
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const r = await postProjectVerificationBillboardUpload(
      new File(["x"], "valla.jpg", { type: "image/jpeg" }),
    );
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.ocrStatus).toBe("success");
      expect(r.ocrQualityHint).toBe("high");
      expect(r.manualPrefill.developer).toBe("Dev");
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

  it("normalizes headline/rationale payloads (strings)", async () => {
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

  it("normalizes headline/rationale key envelopes", async () => {
    process.env.CASASEGURA_API_BASE_URL = "http://example.test";
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            verdict: "green",
            headline_key: "pv.headline.green.demo",
            rationale_keys: ["pv.reputation.skipped_disabled"],
            data_freshness_note_key: "pv.freshness.demo",
          }),
      }),
    );
    const out = await fetchProjectVerificationDemoResult(undefined);
    expect(out?.verdict).toBe("green");
    expect(out?.headline?.length ?? 0).toBeGreaterThan(0);
    expect(out?.rationale.length ?? 0).toBeGreaterThan(0);
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
