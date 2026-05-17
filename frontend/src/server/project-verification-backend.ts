/**
 * Server-only calls to optional project verification stub API (CS-356).
 * Do not log raw form payloads beyond what errors require.
 */

import {
  mapBackendError,
  missingBaseUrlFallback,
} from "@/lib/backend-error-map";
import { normalizeProjectVerificationDemoResult } from "@/lib/project-verification-demo-normalize";
import type { ProjectVerificationResultPreview } from "@/lib/project-verification-types";
import { readContractApiBase } from "@/server/contract-env";

const MANUAL_PATH = "/api/v1/project-verification/manual/";
const BILLBOARD_UPLOAD_PATH = "/api/v1/project-verification/billboard-upload/";
const DEMO_RESULT_PATH = "/api/v1/project-verification/demo-result/";

const DEFAULT_ACCEPT = { Accept: "application/json" } as const;

const MANUAL_POST_TIMEOUT_MS = 30_000;
const BILLBOARD_UPLOAD_TIMEOUT_MS = 30_000;

export type ManualVerificationEcho = {
  developer: string;
  project: string;
  permit: string;
  address: string;
};

export type ManualVerificationPostOk = {
  ok: true;
  referenceId: string;
  echo: ManualVerificationEcho;
  detail?: string;
  stub?: boolean;
};

export type ManualVerificationPostFail = {
  ok: false;
  status: number;
  body: unknown;
};

export type ManualVerificationPostResult =
  | ManualVerificationPostOk
  | ManualVerificationPostFail;

export type BillboardUploadPostOk = {
  ok: true;
  detail?: string;
  stub?: boolean;
  /** OCR / stubs may attach structured hints for `/manual`. */
  prefills?: Partial<ManualVerificationEcho>;
};

export type BillboardUploadPostFail = {
  ok: false;
  status: number;
  body: unknown;
};

export type BillboardUploadPostResult =
  | BillboardUploadPostOk
  | BillboardUploadPostFail;

function manualUrl(base: string): string {
  return `${base}${MANUAL_PATH}`;
}

function billboardUploadUrl(base: string): string {
  return `${base}${BILLBOARD_UPLOAD_PATH}`;
}

function readEchoFields(e: Record<string, unknown>): ManualVerificationEcho | null {
  const pick = (k: string, ...alts: string[]) => {
    for (const key of [k, ...alts]) {
      const v = e[key];
      if (typeof v === "string") return v.trim();
    }
    return "";
  };
  const developer = pick("developer");
  const project = pick("project");
  const permit = pick("permit");
  const address = pick("address");
  if (!developer && !project && !permit && !address) return null;
  return { developer, project, permit, address };
}

function pickEchoEnvelope(raw: Record<string, unknown>): Record<string, unknown> | null {
  const candidates = [
    raw.echo,
    raw.manual_prefill,
    raw.manualPrefill,
    raw.prefill_echo,
    raw.prefillEcho,
  ];
  for (const c of candidates) {
    if (typeof c === "object" && c !== null) {
      return c as Record<string, unknown>;
    }
  }
  return null;
}

/**
 * Parses manual echo/prefill objects from Django/FE JSON envelopes (camelCase + snake_case).
 */
export function parseManualVerificationEcho(
  envelope: Record<string, unknown>,
): ManualVerificationEcho | null {
  const nested = pickEchoEnvelope(envelope);
  if (nested) {
    return readEchoFields(nested);
  }
  return readEchoFields(envelope);
}

export async function postProjectVerificationManual(payload: {
  developer: string;
  project: string;
  permit: string;
  address: string;
}): Promise<ManualVerificationPostResult> {
  const base = readContractApiBase();
  if (!base)
    return {
      ok: false,
      status: 0,
      body: { error_code: "configuration_missing" },
    };

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), MANUAL_POST_TIMEOUT_MS);
  try {
    const res = await fetch(manualUrl(base), {
      method: "POST",
      headers: { ...DEFAULT_ACCEPT, "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
      redirect: "follow",
      signal: controller.signal,
    });
    clearTimeout(t);
    let jsonBody: unknown;
    try {
      jsonBody = await res.clone().json();
    } catch {
      jsonBody = null;
    }
    if (!res.ok) return { ok: false, status: res.status, body: jsonBody };

    const body = jsonBody as Record<string, unknown>;
    const refRaw = body.reference_id ?? body.referenceId;
    const referenceId = typeof refRaw === "string" ? refRaw.trim() : "";
    if (!referenceId)
      return {
        ok: false,
        status: res.status || 502,
        body: { error_code: "invalid_manual_response" },
      };

    const echo = parseManualVerificationEcho(body);
    if (!echo)
      return {
        ok: false,
        status: res.status || 502,
        body: { error_code: "invalid_manual_response" },
      };

    const detail =
      typeof body.detail === "string" && body.detail.trim()
        ? body.detail.trim()
        : undefined;
    const stub = body.stub === true;

    return { ok: true, referenceId, echo, detail, stub };
  } catch {
    clearTimeout(t);
    return { ok: false, status: 0, body: null };
  }
}

/** Returns mapped UX message for failed manual POST (403 disabled, network, etc.). */
export function mapManualVerificationPostFailure(
  fail: ManualVerificationPostFail,
): {
  uiMessage: string;
  category: ReturnType<typeof mapBackendError>["category"];
} {
  if (fail.status === 0 && fail.body && typeof fail.body === "object") {
    const code = (fail.body as { error_code?: string }).error_code;
    if (code === "configuration_missing") {
      const m = missingBaseUrlFallback();
      return { uiMessage: m.uiMessage, category: m.category };
    }
  }
  const m = mapBackendError(fail.body, fail.status);
  return { uiMessage: m.uiMessage, category: m.category };
}

export async function postProjectVerificationBillboardUpload(
  image: File,
): Promise<BillboardUploadPostResult> {
  const base = readContractApiBase();
  if (!base)
    return {
      ok: false,
      status: 0,
      body: { error_code: "configuration_missing" },
    };

  const body = new FormData();
  body.append("image", image, image.name || "billboard-upload");

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), BILLBOARD_UPLOAD_TIMEOUT_MS);
  try {
    const res = await fetch(billboardUploadUrl(base), {
      method: "POST",
      headers: DEFAULT_ACCEPT,
      body,
      cache: "no-store",
      redirect: "follow",
      signal: controller.signal,
    });
    clearTimeout(t);

    let jsonBody: unknown;
    try {
      jsonBody = await res.clone().json();
    } catch {
      jsonBody = null;
    }
    if (!res.ok) return { ok: false, status: res.status, body: jsonBody };

    const raw = jsonBody as Record<string, unknown> | null;
    const detail =
      raw && typeof raw.detail === "string" && raw.detail.trim()
        ? raw.detail.trim()
        : undefined;
    const stub = Boolean(raw && raw.stub === true);
    const parsedEcho = raw ? parseManualVerificationEcho(raw) : null;
    const prefills: Partial<ManualVerificationEcho> = {};
    if (parsedEcho) {
      if (parsedEcho.developer.trim()) prefills.developer = parsedEcho.developer;
      if (parsedEcho.project.trim()) prefills.project = parsedEcho.project;
      if (parsedEcho.permit.trim()) prefills.permit = parsedEcho.permit;
      if (parsedEcho.address.trim()) prefills.address = parsedEcho.address;
    }
    const hasPrefills = Object.keys(prefills).length > 0;
    return {
      ok: true,
      detail,
      stub,
      ...(hasPrefills ? { prefills } : {}),
    };
  } catch {
    clearTimeout(t);
    return { ok: false, status: 0, body: null };
  }
}

/** Returns mapped UX message for failed billboard upload POST (403 disabled, network, etc.). */
export function mapBillboardUploadPostFailure(fail: BillboardUploadPostFail): {
  uiMessage: string;
  category: ReturnType<typeof mapBackendError>["category"];
} {
  if (fail.status === 0 && fail.body && typeof fail.body === "object") {
    const code = (fail.body as { error_code?: string }).error_code;
    if (code === "configuration_missing") {
      const m = missingBaseUrlFallback();
      return { uiMessage: m.uiMessage, category: m.category };
    }
  }
  const m = mapBackendError(fail.body, fail.status);
  return { uiMessage: m.uiMessage, category: m.category };
}

export async function fetchProjectVerificationDemoResult(
  verdictParam: string | undefined,
): Promise<ProjectVerificationResultPreview | null> {
  const base = readContractApiBase();
  if (!base) return null;
  const v = (verdictParam ?? "yellow").trim().toLowerCase() || "yellow";
  const url = `${base}${DEMO_RESULT_PATH}?${new URLSearchParams({ v })}`;
  try {
    const res = await fetch(url, {
      method: "GET",
      headers: DEFAULT_ACCEPT,
      cache: "no-store",
      redirect: "follow",
    });
    if (!res.ok) return null;
    let raw: unknown;
    try {
      raw = await res.json();
    } catch {
      return null;
    }
    return normalizeProjectVerificationDemoResult(raw);
  } catch {
    return null;
  }
}
