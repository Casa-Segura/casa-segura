import { describe, expect, it } from "vitest";
import { classifyPollPayload } from "./contract-backend";

describe("classifyPollPayload", () => {
  it("reports completed terminal", () => {
    expect(classifyPollPayload({ processing_status: "completed", analysis: {} })).toEqual({
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

  it("does not treat failed extraction as not analyzeable outcome", () => {
    expect(classifyPollPayload({ processing_status: "failed_extraction" }).kind).toBe(
      "failed",
    );
  });
});
