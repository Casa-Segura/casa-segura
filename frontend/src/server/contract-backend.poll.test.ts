import { describe, expect, it } from "vitest";
import { classifyPollPayload } from "./contract-backend";

describe("classifyPollPayload", () => {
  it("reports completed terminal", () => {
    expect(classifyPollPayload({ processing_status: "completed", analysis: {} })).toMatchObject({
      kind: "completed",
      analysisHint: {},
    });
  });

  it("uses band not_analyzable with reasons bucket", () => {
    expect(
      classifyPollPayload({
        processing_status: "analyzing",
        band: "not_analyzable",
        not_analyzable_reasons: ["Texto muy bajo"],
      }),
    ).toEqual({
      kind: "not_analyzable",
      reasons: ["Texto muy bajo"],
    });
  });

  it("exposes public_short_id on completed handoff", () => {
    expect(
      classifyPollPayload({
        processing_status: "completed",
        analysis: {},
        public_short_id: "CS-2026-TEST01",
      }),
    ).toMatchObject({
      kind: "completed",
      analysisHint: {},
      publicShortId: "CS-2026-TEST01",
    });
  });

  it("reads public_short_id nested under analysis", () => {
    expect(
      classifyPollPayload({
        processing_status: "completed",
        analysis: { public_short_id: "CS-2026-NESTED" },
      }),
    ).toMatchObject({
      kind: "completed",
      publicShortId: "CS-2026-NESTED",
    });
  });

  it("does not treat failed extraction as not analyzeable outcome", () => {
    expect(classifyPollPayload({ processing_status: "failed_extraction" }).kind).toBe(
      "failed",
    );
  });
});
