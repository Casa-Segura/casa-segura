"use server";

import { redirect } from "next/navigation";
import { validateManualVerificationFields } from "@/app/verificacion-proyecto/manual/validation";
import { isProjectVerificationEnabled } from "@/lib/project-verification-env";
import {
  mapManualVerificationPostFailure,
  postProjectVerificationManual,
} from "@/server/project-verification-backend";

export type ManualFormState =
  | {
      ok: true;
      message: string;
      referenceId?: string;
    }
  | { ok: false; fieldErrors: Record<string, string> }
  | { ok: false; formError: string };

const STUB_OK_MESSAGE =
  "Validación lista en el servidor (sin API remota). Cuando configures CASASEGURA_API_BASE_URL, estos datos se enviarán al mismo contrato que use la verificación asistida por visión.";

const DEV_NETWORK_HINT =
  " Si estás en local, revisá que el backend esté en marcha y que la URL en CASASEGURA_API_BASE_URL sea correcta.";

/**
 * Validates manual fields and, when the gate + API base are set, POSTs to Django stub
 * `POST /api/v1/project-verification/manual/` (CS-351 / CS-356).
 */
export async function submitProjectVerificationManual(
  _prev: ManualFormState | null,
  formData: FormData,
): Promise<ManualFormState> {
  const fields = {
    developer: String(formData.get("developer") ?? ""),
    project: String(formData.get("project") ?? ""),
    permit: String(formData.get("permit") ?? ""),
    address: String(formData.get("address") ?? ""),
  };

  const fieldErrors = validateManualVerificationFields(fields);
  if (fieldErrors) {
    return { ok: false, fieldErrors };
  }

  if (!isProjectVerificationEnabled()) {
    return { ok: true, message: STUB_OK_MESSAGE };
  }

  const post = await postProjectVerificationManual({
    developer: fields.developer.trim(),
    project: fields.project.trim(),
    permit: fields.permit.trim(),
    address: fields.address.trim(),
  });

  if (post.ok) {
    redirect(
      `/verificacion-proyecto/manual/listo?${new URLSearchParams({
        ref: post.referenceId,
      })}`,
    );
  }

  const { uiMessage } = mapManualVerificationPostFailure(post);
  let formError = uiMessage;
  if (post.status === 0 && process.env.NODE_ENV === "development") {
    formError += DEV_NETWORK_HINT;
  }
  return { ok: false, formError };
}
