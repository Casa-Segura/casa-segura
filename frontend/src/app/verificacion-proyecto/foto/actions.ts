"use server";

import { isProjectVerificationEnabled } from "@/lib/project-verification-env";
import { mapBackendError } from "@/lib/backend-error-map";
import {
  mapBillboardUploadPostFailure,
  postProjectVerificationBillboardUpload,
} from "@/server/project-verification-backend";
import { buildManualVerificationHandoffPath } from "@/lib/project-verification-manual-handoff";

export type BillboardUploadFormState =
  | {
      ok: true;
      message: string;
      detail?: string;
      manualHandoffHref: string;
    }
  | { ok: false; formError: string };

const BILLBOARD_FIELD = "billboard";
const BILLBOARD_MAX_BYTES = 15 * 1024 * 1024;
const BILLBOARD_ALLOWED_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/webp",
  "image/heic",
  "image/heif",
]);

const DEV_NETWORK_HINT =
  " Si estás en local, revisá que el backend esté en marcha y que la URL en CASASEGURA_API_BASE_URL sea correcta.";

function formatMb(bytes: number): string {
  return `${Math.round(bytes / 1024 / 1024)} MB`;
}

function validateBillboardFile(
  value: FormDataEntryValue | null,
): File | string {
  if (!(value instanceof File) || value.size === 0) {
    return "Elegí una foto de la valla antes de enviar.";
  }
  if (!BILLBOARD_ALLOWED_TYPES.has(value.type)) {
    return "Usá una imagen JPEG, PNG, WEBP o HEIC.";
  }
  if (value.size > BILLBOARD_MAX_BYTES) {
    return `La foto supera ${formatMb(BILLBOARD_MAX_BYTES)}. Tomá otra foto más liviana o reducí el archivo.`;
  }
  return value;
}

export async function submitProjectVerificationBillboardUpload(
  _prev: BillboardUploadFormState | null,
  formData: FormData,
): Promise<BillboardUploadFormState> {
  const fileOrError = validateBillboardFile(formData.get(BILLBOARD_FIELD));
  if (typeof fileOrError === "string") {
    return { ok: false, formError: fileOrError };
  }

  if (!isProjectVerificationEnabled()) {
    const m = mapBackendError(
      { error_code: "project_verification_disabled" },
      403,
    );
    return { ok: false, formError: m.uiMessage };
  }

  const post = await postProjectVerificationBillboardUpload(fileOrError);
  if (post.ok) {
    const manualHandoffHref = buildManualVerificationHandoffPath({
      ...(post.prefills ?? {}),
      source: "billboard_stub_continue",
    });
    return {
      ok: true,
      message: post.stub
        ? "Foto recibida por el stub. La imagen se descarta sin guardarla; el OCR real se conectará después."
        : "Foto recibida. Cuando el backend tenga OCR real, acá seguirá la lectura automática.",
      detail: post.detail,
      manualHandoffHref,
    };
  }

  const { uiMessage } = mapBillboardUploadPostFailure(post);
  let formError = uiMessage;
  if (post.status === 0 && process.env.NODE_ENV === "development") {
    formError += DEV_NETWORK_HINT;
  }
  return { ok: false, formError };
}
