import { describe, expect, it } from "vitest";
import {
  EXPIRED_ANALYSIS_PRIVACY_LINE,
  EXPIRED_ANALYSIS_UNAVAILABLE,
} from "./expired-link-copy";

describe("expired-link-copy / PRD_GENERAL US-05", () => {
  it("matches PRD US-05 primary sentences", () => {
    const composed =
      `${EXPIRED_ANALYSIS_UNAVAILABLE} ${EXPIRED_ANALYSIS_PRIVACY_LINE}`.trim();
    expect(composed).toBe(
      "Este análisis ya no está disponible. Casa Segura no almacena reportes de forma permanente para proteger tu privacidad.",
    );
  });
});
