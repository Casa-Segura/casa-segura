/**
 * Maps CS-009 `error_code` strings from the Casa Segura JSON envelope into safe Spanish UX copy.
 */

const SPANISH_DEFAULT = "Algo salió mal. Intentá otra vez en unos segundos.";
const SPANISH_5XX =
  "El servicio tardó más de lo previsto o no está disponible. Probá más tarde.";
const SPANISH_NETWORK =
  "No pudimos conectar. Revisá tu conexión y volvé a intentarlo.";
const SPANISH_NOT_CONFIGURED =
  "Este entorno no tiene configurado el servidor de Casa Segura (CASASEGURA_API_BASE_URL).";

/** Uppercase semantic codes from PRD F1 / ingestion (and stable aliases). */
const TABLE = {
  DISCLAIMER_REQUIRED:
    "Tenés que confirmar el aviso legal antes de enviar. Marcá la casilla y probá de nuevo.",
  FILE_TOO_LARGE:
    "Uno de los archivos pesa más de 15 MB. Reducí el tamaño o dividí el documento antes de enviar.",
  TOTAL_SIZE_TOO_LARGE:
    "En conjunto superan los 100 MB permitidos por envío. Quitá algunos archivos antes de continuar.",
  TOO_MANY_FILES:
    "Sólo podés enviar hasta 50 archivos en un mismo envío. Quitá algunos antes de continuar.",
  TOO_MANY_PAGES:
    "Superaste el límite de páginas (máx. ~50 por PDF y ~80 en total). Revisá o dividí tus PDF antes de intentar.",
  FORMAT_NOT_SUPPORTED:
    "Uno de los archivos no está en formato permitido. Usá PDF, JPEG, PNG, HEIC o WEBP.",
  IMAGE_DIMENSIONS_INVALID:
    "Una imagen tiene medidas muy pequeñas o muy grandes. Probá otro archivo o foto más nítida.",
  INVALID_DELIVERY_CHANNEL: "Elegí de nuevo cómo querés recibir el resultado.",
  INVALID_DELIVERY_TARGET:
    "Revisá el correo o el número (formato internacional con +); el servidor lo rechazó.",
  FILE_EMPTY: "Uno de los archivos está vacío. Exportá otro archivo e intentá otra vez.",
  PDF_NOT_SAFE:
    "Ese PDF no se puede procesar de forma segura ahora mismo. Exportá uno nuevo o fotografiá las páginas.",
  VALIDATION_ERROR:
    "Faltan datos o hay errores en el envío. Revisá tus archivos y las opciones elegidas.",
  RATE_LIMITED:
    "Llegamos al cupo temporal de envíos. Esperá un momento antes de volver a intentarlo.",
  THROTTLED:
    "Llegamos al cupo temporal de envíos. Esperá un momento antes de volver a intentarlo.",
} as const satisfies Record<string, string>;

export type ApiErrorEnvelope = {
  error_code?: string;
  message?: string;
};

function canonicalCode(raw?: string): keyof typeof TABLE | null {
  if (typeof raw !== "string") return null;
  let s = raw.trim();
  if (!s) return null;
  if (s.includes(".")) {
    const segs = s.split(".");
    s = segs[segs.length - 1]!.trim();
  }
  const up = s.replace(/-/g, "_").toUpperCase();
  return up in TABLE ? (up as keyof typeof TABLE) : null;
}

export type MappedUserFacingError = {
  category: "disclaimer" | "business" | "server" | "network" | "not_found" | "unknown" | "configuration";
  code?: string;
  uiMessage: string;
};

function looksUnsafeInternalCopy(msg: string): boolean {
  if (/ENOTFOUND|EAI_AGAIN|ECONNREFUSED|fetch failed|AxiosError/i.test(msg)) return true;
  if (/\sat\s\S+\(.*:\d+:\d+\)/.test(msg)) return true;
  return msg.length > 240;
}

export function mapBackendError(body: unknown, httpStatus: number): MappedUserFacingError {
  if (httpStatus === 0 || Number.isNaN(httpStatus))
    return { category: "network", uiMessage: SPANISH_NETWORK };
  if (httpStatus >= 500) return { category: "server", uiMessage: SPANISH_5XX };

  let rawCode: string | undefined;
  if (typeof body === "object" && body !== null && "error_code" in body) {
    const ec = (body as ApiErrorEnvelope).error_code;
    rawCode = typeof ec === "string" ? ec : undefined;
  }

  const key = canonicalCode(rawCode ?? "");
  if (httpStatus === 404) return { category: "not_found", uiMessage: SPANISH_DEFAULT, code: rawCode };

  if (key) {
    return {
      category: key === "DISCLAIMER_REQUIRED" ? "disclaimer" : "business",
      code: rawCode,
      uiMessage: TABLE[key],
    };
  }

  if (typeof body === "object" && body !== null && "error_code" in body) {
    const env = body as ApiErrorEnvelope;
    const pick = typeof env.message === "string" ? env.message.trim() : "";
    if (!looksUnsafeInternalCopy(pick) && pick.length > 3) {
      if (pick.toLowerCase().includes("disclaimer"))
        return { category: "disclaimer", uiMessage: TABLE.DISCLAIMER_REQUIRED };
      return { category: "business", code: rawCode, uiMessage: localizeDevEnglish(pick) };
    }
  }

  if (httpStatus === 413)
    return { category: "business", code: rawCode ?? "payload_too_large", uiMessage: TABLE.FILE_TOO_LARGE };

  if (httpStatus === 429) return { category: "business", code: rawCode ?? "RATE_LIMITED", uiMessage: TABLE.RATE_LIMITED };

  return { category: httpStatus >= 400 ? "business" : "unknown", uiMessage: SPANISH_DEFAULT, code: rawCode };
}

function localizeDevEnglish(pick: string): string {
  const l = pick.toLowerCase();
  if (l.includes("request payload failed validation")) return TABLE.VALIDATION_ERROR;
  /** Default: fall back rather than exposing unknown English verbatim */
  return SPANISH_DEFAULT;
}

export function missingBaseUrlFallback(): MappedUserFacingError {
  return { category: "configuration", uiMessage: SPANISH_NOT_CONFIGURED };
}
