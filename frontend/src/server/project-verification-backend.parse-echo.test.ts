import { describe, expect, it } from "vitest";
import {
  parseManualVerificationEcho,
} from "@/server/project-verification-backend";

describe("parseManualVerificationEcho", () => {
  it("parses nested echo payloads", () => {
    expect(
      parseManualVerificationEcho({
        echo: {
          developer: "  Dev ",
          project: "",
          permit: "p",
          address: "",
        },
      }),
    ).toEqual({
      developer: "Dev",
      project: "",
      permit: "p",
      address: "",
    });
  });

  it("prefers OCR-style manual_prefill when present", () => {
    expect(
      parseManualVerificationEcho({
        manual_prefill: {
          developer: "Dev",
          project: "Proj",
          permit: "",
          address: "",
        },
      }),
    ).toEqual({
      developer: "Dev",
      project: "Proj",
      permit: "",
      address: "",
    });
  });
});
