import { describe, expect, it } from "vitest";
import {
  MANUAL_VERIFICATION_MAX_LEN,
  validateManualVerificationFields,
} from "@/app/verificacion-proyecto/manual/validation";

const okRow = {
  developer: "ACME",
  project: "Torre Norte",
  permit: "12345",
  address: "San Salvador",
};

describe("validateManualVerificationFields", () => {
  it("returns null when all fields valid", () => {
    expect(validateManualVerificationFields(okRow)).toBeNull();
  });

  it("rejects whitespace-only permit", () => {
    const r = validateManualVerificationFields({ ...okRow, permit: "   " });
    expect(r?.permit).toMatch(/permiso/i);
  });

  it("rejects overflow", () => {
    const long = "x".repeat(MANUAL_VERIFICATION_MAX_LEN + 1);
    const r = validateManualVerificationFields({ ...okRow, developer: long });
    expect(r?.developer).toMatch(/Máximo/);
  });

  it("accepts multiline address after trim", () => {
    expect(
      validateManualVerificationFields({
        ...okRow,
        address: "  Barrio Centro\nentre calles 1 y 3  ",
      }),
    ).toBeNull();
  });
});
