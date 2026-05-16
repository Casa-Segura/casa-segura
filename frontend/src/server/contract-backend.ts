/**
 * Proxies multipart upload + exponential-ish polling toward CASASEGURA_API_BASE_URL.
 * Do not console.log buffers, multipart bodies, or delivery targets — only sanitized codes/status.
 */

import { mapBackendError, missingBaseUrlFallback } from "@/lib/backend-error-map";
import {
  readContractApiBase,
  readPollBackoffMsSeries,
  readPollBudgetMs,
  readSubmissionStatusTemplate,
  readSubmitPath,
  readSubmitTimeoutMs,
  readUploadEnabled,
} from "@/server/contract-env";

const DEFAULT_HEADERS_ACCEPT = {
  Accept: "application/json",
};

export type SubmissionPostResult =
  | { ok: true; submissionId: string }
  | { ok: false; status: number; body: unknown };

export async function forwardContractSubmissionMultipart(
  inbound: FormData,
): Promise<SubmissionPostResult> {
  const base = readContractApiBase();
  if (!base)
    return { ok: false, status: 0, body: { error_code: "configuration_missing" } };

  const path = readSubmitPath();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), readSubmitTimeoutMs());
  try {
    const upstream = await fetch(url, {
      method: "POST",
      headers: DEFAULT_HEADERS_ACCEPT,
      body: inbound,
      redirect: "follow",
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(t);
    let jsonBody: unknown;
    try {
      jsonBody = await upstream.clone().json();
    } catch {
      jsonBody = null;
    }
    if (!upstream.ok) return { ok: false, status: upstream.status, body: jsonBody };

    const id = extractSubmissionId(jsonBody as Record<string, unknown>);
    if (!id)
      return { ok: false, status: upstream.status || 502, body: { error_code: "invalid_submit_response" } };
    return { ok: true, submissionId: id };
  } catch {
    clearTimeout(t);
    return { ok: false, status: 0, body: null };
  }
}

function extractSubmissionId(body: Record<string, unknown>): string | null {
  const a = body["submission_id"] ?? body["submissionId"];
  const b = body["id"];
  const raw = typeof a === "string" ? a : typeof b === "string" ? b : "";
  const id = typeof raw === "string" ? raw.trim() : "";
  return id.length ? id : null;
}

export type PollTerminal =
  | {
      kind: "completed";
      analysisHint?: unknown;
      /** Present when BE surfaces `public_short_id` for `web_link` handoff (CS-294). */
      publicShortId?: string;
      linkExpiresAt?: string;
    }
  | { kind: "not_analyzable"; reasons: string[] }
  | { kind: "failed"; message: string };

function readExpiresAt(payload: Record<string, unknown>): string | undefined {
  const keys = ["link_expires_at", "linkExpiresAt", "expires_at", "expiresAt"] as const;
  for (const k of keys) {
    const v = payload[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return undefined;
}

function readPublicShortIdFromRecord(obj: Record<string, unknown>): string | undefined {
  const raw = obj["public_short_id"] ?? obj["publicShortId"];
  if (typeof raw !== "string") return undefined;
  const s = raw.trim();
  return s.length ? s : undefined;
}

/** Pulls capability token + optional expiry from poll payloads (tolerant shapes until OpenAPI is final). */
export function extractCompletedHandoffMeta(payload: Record<string, unknown>): {
  publicShortId?: string;
  linkExpiresAt?: string;
} {
  let publicShortId = readPublicShortIdFromRecord(payload);
  let linkExpiresAt = readExpiresAt(payload);

  const analysis = payload["analysis"];
  if (typeof analysis === "object" && analysis !== null) {
    const arec = analysis as Record<string, unknown>;
    if (!publicShortId) publicShortId = readPublicShortIdFromRecord(arec);
    if (!linkExpiresAt) linkExpiresAt = readExpiresAt(arec);
  }

  return { publicShortId, linkExpiresAt };
}

function processingStatus(payload: Record<string, unknown>): string {
  const raw = payload["processing_status"] ?? payload["processingStatus"] ?? "";
  return typeof raw === "string" ? raw.trim().toLowerCase() : "";
}

function rejectionReasons(payload: Record<string, unknown>): string[] {
  const keys = ["not_analyzable_reasons", "rejection_reasons", "reasons"];
  const out: string[] = [];
  for (const k of keys) {
    const raw = payload[k];
    if (Array.isArray(raw)) {
      for (const row of raw) {
        if (typeof row === "string" && row.trim()) out.push(row.trim());
      }
      if (out.length > 0) return out;
    }
  }
  const msg =
    typeof payload["error_reason"] === "string" ? payload["error_reason"].trim() : "";
  const code = typeof payload["error_code"] === "string" ? payload["error_code"].trim() : "";
  if (msg) return [msg];
  if (code) return [code.replace(/_/g, " ").toUpperCase()];
  return ["Este contrato entró como no analizable. Prueba otro archivo o fotografía más legible."];
}

const IN_PROGRESS = new Set([
  "received",
  "extracting",
  "extracted",
  "classifying",
  "analyzing",
]);

/** Interprets a single poll JSON blob and returns terminal outcome or tells caller to retry. */
export function classifyPollPayload(payload: Record<string, unknown>):
  | PollTerminal
  | { kind: "continue" } {
  const st = processingStatus(payload);
  const band = typeof payload["band"] === "string" ? payload["band"].trim().toLowerCase() : "";

  if (st === "completed") {
    const { publicShortId, linkExpiresAt } = extractCompletedHandoffMeta(payload);
    return {
      kind: "completed",
      analysisHint: payload["analysis"],
      publicShortId,
      linkExpiresAt,
    };
  }

  if (band === "not_analyzable") {
    return { kind: "not_analyzable", reasons: rejectionReasons(payload) };
  }

  if (IN_PROGRESS.has(st)) return { kind: "continue" };

  if (st === "expired" || /^failed_/i.test(st) || /^rejected_/i.test(st)) {
    const reasons = rejectionReasons(payload);
    return {
      kind: "failed",
      message: reasons[0] ?? "Tu envío terminó antes de obtener un informe. Prueba otro formato.",
    };
  }

  /** Empty/intermediate payloads — carry on until poll budget exhausts */
  if (!st) return { kind: "continue" };

  return {
    kind: "failed",
    message:
      rejectionReasons(payload)[0] ??
      `El proceso terminó antes de tiempo (estado: ${st}). Inténtalo otra vez.`,
  };
}

async function pollOnce(base: string, template: string, submissionId: string): Promise<unknown | null> {
  const tail = template.replace("{{id}}", encodeURIComponent(submissionId));
  const url = `${base}${tail.startsWith("/") ? tail : `/${tail}`}`;
  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), 25_000);
  try {
    const res = await fetch(url, {
      method: "GET",
      headers: DEFAULT_HEADERS_ACCEPT,
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(t);
    if (!res.ok) return { status_proxy: res.status };
    try {
      return await res.json();
    } catch {
      return null;
    }
  } catch {
    clearTimeout(t);
    return null;
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export async function pollSubmissionUntilTerminal(
  submissionId: string,
): Promise<PollTerminal | { kind: "timeout" }> {
  const base = readContractApiBase();
  if (!base) return { kind: "timeout" };
  const template = readSubmissionStatusTemplate();

  const series = [...readPollBackoffMsSeries()];
  const deadlineMs = Date.now() + readPollBudgetMs();

  for (let i = 0; Date.now() < deadlineMs; i++) {
    const waitMs = Math.min(series[Math.min(i, series.length - 1)] ?? 5000, 10_000);
    await delay(waitMs);
    const raw = await pollOnce(base, template, submissionId);
    const payload =
      typeof raw === "object" && raw !== null ? (raw as Record<string, unknown>) : {};

    /** Non-JSON / proxy status — soften and continue briefly */
    if ("status_proxy" in payload && typeof payload.status_proxy === "number") {
      if (payload.status_proxy >= 500) continue;
      if (payload.status_proxy === 404) return { kind: "timeout" };
      continue;
    }

    const next = classifyPollPayload(payload);
    if (next.kind !== "continue") return next;
  }

  return { kind: "timeout" };
}

export type FlowResult =
  | {
      outcome: "success";
      submissionId: string;
      analysisHint?: unknown;
      channelSummary: string;
      publicShortId?: string;
      linkExpiresAt?: string;
    }
  | {
      outcome: "not_analyzable";
      submissionId: string;
      reasons: string[];
      channelSummary: string;
    }
  | {
      outcome: "error";
      message: string;
      disclaimerRequired?: boolean;
      fatal?: boolean;
    };

/** Joins multipart forward + backoff polling inside the Server Action (single client round-trip). */
export async function runContractSubmissionServerFlow(formData: FormData): Promise<FlowResult> {
  if (!readUploadEnabled())
    return {
      outcome: "error",
      message:
        "La subida desde web está temporalmente desactivada. Prueba más tarde o contacta soporte.",
      fatal: false,
    };

  const base = readContractApiBase();
  if (!base)
    return {
      outcome: "error",
      fatal: false,
      message: missingBaseUrlFallback().uiMessage,
    };

  /** Never log multipart body or filenames */
  const post = await forwardContractSubmissionMultipart(formData);
  const channelHuman = summarizeChannelFromFd(formData);
  if (!post.ok) {
    const mapped = mapBackendError(post.body, post.status);
    return {
      outcome: "error",
      message: mapped.uiMessage,
      disclaimerRequired: mapped.category === "disclaimer",
    };
  }

  const terminal = await pollSubmissionUntilTerminal(post.submissionId);
  if ("kind" in terminal && terminal.kind === "timeout") {
    return {
      outcome: "error",
      fatal: false,
      message:
        "Seguimos analizándolo en servidor; la consulta tardó más de lo que podemos mostrar desde aquí. Si no recibes nada por el canal elegido, vuelve a intentar dentro de varios minutos.",
    };
  }

  if (terminal.kind === "completed")
    return {
      outcome: "success",
      submissionId: post.submissionId,
      analysisHint: terminal.analysisHint,
      channelSummary: channelHuman,
      publicShortId: terminal.publicShortId,
      linkExpiresAt: terminal.linkExpiresAt,
    };

  if (terminal.kind === "not_analyzable")
    return {
      outcome: "not_analyzable",
      submissionId: post.submissionId,
      reasons: terminal.reasons,
      channelSummary: channelHuman,
    };

  return {
    outcome: "error",
    message: terminal.message,
  };
}

function summarizeChannelFromFd(fd: FormData): string {
  const ch = `${fd.get("delivery_channel") ?? ""}`;
  switch (ch) {
    case "email_pdf":
      return "Recibirás un PDF si el proceso termina bien.";
    case "whatsapp_summary":
      return "Te escribimos por WhatsApp con un breve resumen cuando esté.";
    default:
      return "Podrás abrir tu informe desde un enlace cuando esté listo.";
  }
}
