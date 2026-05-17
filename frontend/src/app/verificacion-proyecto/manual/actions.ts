"use server";

import { redirect } from "next/navigation";
import { validateManualVerificationFields } from "@/app/verificacion-proyecto/manual/validation";
import {
  isProjectVerificationEnabled,
} from "@/lib/project-verification-env";
import {
  mapManualVerificationPostFailure,
  postProjectVerificationManual,
} from "@/server/project-verification-backend";
import {
  setProjectVerificationVerdictFlashFromManualOk,
} from "@/server/project-verification-verdict-flash-cookie";

export type ManualFormState =
  | {
      ok: true;
      message: string;
    }
  | { ok: false; fieldErrors: Record<string, string> }
  | { ok: false; formError: string };

const OFFLINE_OK_MESSAGE =
  "Verificación de proyecto desactivada en este ambiente front. Probá desde un despliegue que tenga PROJECT_VERIFICATION_ENABLED habilitado y API base configurada.";

const DEV_NETWORK_HINT =
  " Si estás en local, revisá que el backend esté en marcha y que la URL en CASASEGURA_API_BASE_URL sea correcta.";

function readSubmissionMeta(formData: FormData): {
  submission_source: "manual" | "billboard_ocr";
  ocr_quality?: string | null;
} {
  const srcRaw =
    String(formData.get("submission_source") ?? "manual").trim() ===
    "billboard_ocr"
      ? ("billboard_ocr" as const)
      : ("manual" as const);

  let ocr_quality: string | null | undefined;
  if (srcRaw === "billboard_ocr") {
    const raw = formData.get("ocr_quality");
    if (typeof raw !== "string" || !raw.trim()) {
      ocr_quality = undefined;
    } else {
      const q = raw.trim().toLowerCase();
      const allowed = new Set(["high", "medium", "low", "unknown"]);
      ocr_quality = allowed.has(q) ? q : "unknown";
    }
  } else {
    ocr_quality = undefined;
  }

  return { submission_source: srcRaw, ocr_quality };
}

/**
 * Validates manual fields and, when the gate + API base are set, POSTs to Django
 * `POST /api/v1/project-verification/manual/` then flashes short-lived resultado
 * context (HTTP-only cookie) before redirect (CS-351 / CS-355).
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

  const { submission_source, ocr_quality } = readSubmissionMeta(formData);

  if (!isProjectVerificationEnabled()) {
    return { ok: true, message: OFFLINE_OK_MESSAGE };
  }

  const postPayload = {
    developer: fields.developer.trim(),
    project: fields.project.trim(),
    permit: fields.permit.trim(),
    address: fields.address.trim(),
    submission_source,
    ...(ocr_quality !== undefined ? { ocr_quality } : {}),
  };

  const post = await postProjectVerificationManual(postPayload);

  if (post.ok) {
    await setProjectVerificationVerdictFlashFromManualOk(post);
    redirect("/verificacion-proyecto/resultado");
  }

  const { uiMessage } = mapManualVerificationPostFailure(post);
  let formError = uiMessage;
  if (post.status === 0 && process.env.NODE_ENV === "development") {
    formError += DEV_NETWORK_HINT;
  }
  return { ok: false, formError };
}
