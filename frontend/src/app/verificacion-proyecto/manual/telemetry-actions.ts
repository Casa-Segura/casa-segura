"use server";

import type { ManualHandoffSource } from "@/lib/project-verification-manual-handoff";
import { reportProjectVerificationTelemetry } from "@/lib/project-verification-telemetry";

export async function recordManualFormHandoffTelemetry(
  source: ManualHandoffSource | undefined,
): Promise<void> {
  reportProjectVerificationTelemetry({
    event: "project_verification_manual_entry",
    fallback: "manual_form",
    ...(source ? { source } : {}),
  });
}
