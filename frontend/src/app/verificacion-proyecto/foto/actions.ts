"use server";

import { redirect } from "next/navigation";
import { mapBackendError } from "@/lib/backend-error-map";
import { isProjectVerificationEnabled } from "@/lib/project-verification-env";
import {
  buildManualVerificationHandoffPath,
  type ManualHandoffSource,
} from "@/lib/project-verification-manual-handoff";
import { reportProjectVerificationTelemetry } from "@/lib/project-verification-telemetry";
import {
  mapBillboardUploadPostFailure,
  mapManualVerificationPostFailure,
  postProjectVerificationBillboardUpload,
  postProjectVerificationManual,
  type BillboardUploadPostOk,
} from "@/server/project-verification-backend";
import {
  setProjectVerificationVerdictFlashFromManualOk,
} from "@/server/project-verification-verdict-flash-cookie";

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
    return "Usá una imagen JPEG, PNG o WEBP.";
  }
  if (value.size > BILLBOARD_MAX_BYTES) {
    return `La foto supera ${formatMb(BILLBOARD_MAX_BYTES)}. Tomá otra foto más liviana o reducí el archivo.`;
  }
  return value;
}

function mergedBillboardEcho(
  post: BillboardUploadPostOk,
): Record<"developer" | "project" | "permit" | "address", string> {
  const pick = (
    field: "developer" | "project" | "permit" | "address",
  ): string => {
    const fromPref = post.manualPrefill[field];
    const fromFields = post.fields[field];
    const raw =
      typeof fromPref === "string" && fromPref.trim()
        ? fromPref
        : typeof fromFields === "string"
          ? fromFields
          : "";
    return raw.trim();
  };

  return {
    developer: pick("developer"),
    project: pick("project"),
    permit: pick("permit"),
    address: pick("address"),
  };
}

function allEchoFieldsFilled(
  echo: ReturnType<typeof mergedBillboardEcho>,
): boolean {
  return Boolean(
    echo.developer && echo.project && echo.permit && echo.address,
  );
}

function billboardHandoffSource(
  post: BillboardUploadPostOk,
): ManualHandoffSource {
  switch (post.ocrStatus) {
    case "timeout":
      return "ocr_timeout";
    case "low_confidence":
      return "ocr_low_confidence";
    case "failure":
    case "parse_failure":
      return "ocr_failure";
    default:
      return "billboard_stub_continue";
  }
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

  function reportBillboardTelemetry(
    ok: BillboardUploadPostOk,
    routed: "resultado_flash" | "manual_handoff",
  ): void {
    reportProjectVerificationTelemetry({
      event: "project_verification_billboard_completed",
      ocr_status: ok.ocrStatus,
      ocr_quality_hint: ok.ocrQualityHint,
      routed,
    });
  }

  if (!post.ok) {
    const { uiMessage } = mapBillboardUploadPostFailure(post);
    let formError = uiMessage;
    if (post.status === 0 && process.env.NODE_ENV === "development") {
      formError += DEV_NETWORK_HINT;
    }
    return { ok: false, formError };
  }

  const qHint = post.ocrQualityHint.trim().toLowerCase() || "low";

  if (post.ocrStatus === "success" && qHint === "high") {
    const echo = mergedBillboardEcho(post);

    if (allEchoFieldsFilled(echo)) {
      const evaluated = await postProjectVerificationManual({
        ...echo,
        submission_source: "billboard_ocr",
        ocr_quality: qHint,
      });

      if (evaluated.ok) {
        reportBillboardTelemetry(post, "resultado_flash");
        await setProjectVerificationVerdictFlashFromManualOk(evaluated);
        redirect("/verificacion-proyecto/resultado");
      }

      reportBillboardTelemetry(post, "manual_handoff");
      const { uiMessage } = mapManualVerificationPostFailure(evaluated);

      const manualHandoffHref = buildManualVerificationHandoffPath({
        developer: echo.developer,
        project: echo.project,
        permit: echo.permit,
        address: echo.address,
        source: billboardHandoffSource(post),
        ocr_quality: qHint,
      });

      return {
        ok: true,
        message:
          "La lectura se ve muy segura, pero el servidor no terminó la verificación automática esta vez.",
        detail: uiMessage,
        manualHandoffHref,
      };
    }
  }

  reportBillboardTelemetry(post, "manual_handoff");

  const echoForHandoff = mergedBillboardEcho(post);
  const manualHandoffHref = buildManualVerificationHandoffPath({
    developer: echoForHandoff.developer || undefined,
    project: echoForHandoff.project || undefined,
    permit: echoForHandoff.permit || undefined,
    address: echoForHandoff.address || undefined,
    source: billboardHandoffSource(post),
    ocr_quality: qHint,
  });

  const message =
    post.ocrStatus === "success"
      ? "Tomamos la foto sin guardarla. Revisá la sugerencia y enviá el formulario manual si todo cuadra."
      : post.ocrStatus === "timeout"
        ? "La lectura tardó más de lo permitido en este intento."
        : "No pudimos leer la foto con suficiente claridad esta vez.";

  return {
    ok: true,
    message,
    detail: post.detail,
    manualHandoffHref,
  };
}
