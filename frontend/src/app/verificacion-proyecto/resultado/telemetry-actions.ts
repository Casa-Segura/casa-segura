"use server";

import { reportProjectVerificationTelemetry } from "@/lib/project-verification-telemetry";

export async function recordProjectVerificationContractCtaImpression(): Promise<void> {
  reportProjectVerificationTelemetry({
    event: "project_verification_contract_cta_impression",
    route: "/verificacion-proyecto/resultado",
  });
}
