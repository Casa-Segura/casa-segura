/**
 * Privacy-safe instrumentation (CS-351 / CS-355). Never log OCR text, addresses, filenames, or form bodies.
 * Enable structured server logs locally or in staging via `PROJECT_VERIFICATION_TELEMETRY_LOG=true|1`.
 * Intended for server actions / Node only — do not import from client components.
 */
export type ProjectVerificationTelemetryManualEntryPayload = Readonly<{
  event: "project_verification_manual_entry";
  fallback: "manual_form";
  /** Omitted when entry has no validated source token (unknown query dropped at parse layer). */
  source?: string;
}>;

export type ProjectVerificationTelemetryCtaImpressionPayload = Readonly<{
  event: "project_verification_contract_cta_impression";
  route: "/verificacion-proyecto/resultado";
}>;

/** Count-free routing metadata only — never filenames, base64, or OCR text (CS-351). */
export type ProjectVerificationTelemetryBillboardPayload = Readonly<{
  event: "project_verification_billboard_completed";
  ocr_status: string;
  ocr_quality_hint: string;
  routed: "resultado_flash" | "manual_handoff";
}>;

export type ProjectVerificationTelemetryPayload =
  | ProjectVerificationTelemetryManualEntryPayload
  | ProjectVerificationTelemetryBillboardPayload
  | ProjectVerificationTelemetryCtaImpressionPayload;

function isTelemetryLogEnabled(): boolean {
  const raw =
    process.env.PROJECT_VERIFICATION_TELEMETRY_LOG?.trim().toLowerCase();
  return raw === "1" || raw === "true" || raw === "yes";
}

export function reportProjectVerificationTelemetry(
  payload: ProjectVerificationTelemetryPayload,
): void {
  if (!isTelemetryLogEnabled()) return;

  console.info(
    "[project-verification-telemetry]",
    JSON.stringify({
      ...payload,
      at: new Date().toISOString(),
    }),
  );
}
