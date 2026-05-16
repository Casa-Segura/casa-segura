"use server";

import type { FlowResult } from "@/server/contract-backend";
import { runContractSubmissionServerFlow } from "@/server/contract-backend";

export async function submitContractUploadFlow(formData: FormData): Promise<FlowResult> {
  return runContractSubmissionServerFlow(formData);
}
