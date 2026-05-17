/**
 * Server-only calls to optional project verification API (EPIC-12).
 * Do not log raw payloads beyond what errors require.
 */

import {
  mapBackendError,
  missingBaseUrlFallback,
} from "@/lib/backend-error-map";
import { normalizeProjectVerificationDemoResult } from "@/lib/project-verification-demo-normalize";
import type {
  ProjectVerificationResultPreview,
  ProjectVerificationVerdict,
} from "@/lib/project-verification-types";
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
  verdict: ProjectVerificationVerdict;
  rationaleKeys: string[];
  headlineKey: string;
  heuristicScore: number;
  reputationOutcome?: string;
  reputationFetchedAt?: string | null;
  dataFreshnessNoteKey?: string | null;
  permitFindingKey?: string;
  echo: ManualVerificationEcho;
  detail?: string;
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
  ocrStatus: string;
  ocrQualityHint: string;
  fields: Partial<ManualVerificationEcho>;
  manualPrefill: Partial<ManualVerificationEcho>;
  detail?: string;
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

function readEchoFields(
  e: Record<string, unknown>,
): ManualVerificationEcho | null {
  const pick = (k: string, ...alts: string[]) => {
    for (const key of [k, ...alts]) {
      const v = e[key];
      if (typeof v === "string") return v.trim();
      if (v === null || v === undefined) return "";
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

function pickEchoEnvelope(
  raw: Record<string, unknown>,
): Record<string, unknown> | null {
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
  if (nested) return readEchoFields(nested);

  const fields = envelope.fields;
  if (typeof fields === "object" && fields !== null) {
    return readEchoFields(fields as Record<string, unknown>);
  }
  return readEchoFields(envelope);
}

function readString(v: unknown): string | undefined {
  return typeof v === "string" && v.trim() ? v.trim() : undefined;
}

function readOptionalStringRecord(
  o: Record<string, unknown>,
  snake: string,
  camel: string,
): string | null | undefined {
  const raw = o[snake] ?? o[camel];
  if (raw === null) return null;
  if (typeof raw === "string") return raw;
  return undefined;
}

function parseVerdict(
  raw: string | undefined,
): ProjectVerificationVerdict | undefined {
  if (!raw) return undefined;
  if (raw === "green" || raw === "yellow" || raw === "red") return raw;
  return undefined;
}

export async function postProjectVerificationManual(payload: {
  developer: string;
  project: string;
  permit: string;
  address: string;
  submission_source?: "manual" | "billboard_ocr";
  ocr_quality?: string | null;
}): Promise<ManualVerificationPostResult> {
  const base = readContractApiBase();
  if (!base) {
    return {
      ok: false,
      status: 0,
      body: { error_code: "configuration_missing" },
    };
  }

  const bodyPayload: Record<string, unknown> = {
    developer: payload.developer,
    project: payload.project,
    permit: payload.permit,
    address: payload.address,
  };

  if (payload.submission_source) {
    bodyPayload.submission_source = payload.submission_source;
  }
  if (payload.ocr_quality !== undefined) {
    bodyPayload.ocr_quality = payload.ocr_quality;
  }

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), MANUAL_POST_TIMEOUT_MS);
  try {
    const res = await fetch(manualUrl(base), {
      method: "POST",
      headers: { ...DEFAULT_ACCEPT, "Content-Type": "application/json" },
      body: JSON.stringify(bodyPayload),
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

    const record = jsonBody as Record<string, unknown>;
    const refRaw = record.reference_id ?? record.referenceId;
    const referenceId = typeof refRaw === "string" ? refRaw.trim() : "";

    const verdictRaw = parseVerdict(
      typeof record.verdict === "string" ? record.verdict : undefined,
    );
    const headlineKey =
      typeof record.headline_key === "string"
        ? record.headline_key
        : typeof record.headlineKey === "string"
          ? record.headlineKey
          : "";

    const rationalesRaw =
      record.rationale_keys ?? record.rationaleKeys ?? [];
    const rationaleKeys = Array.isArray(rationalesRaw)
      ? rationalesRaw.filter((x): x is string => typeof x === "string")
      : [];

    const heuristicScore = Number(record.heuristic_score ?? record.heuristicScore);

    if (!referenceId || !verdictRaw || !Number.isFinite(heuristicScore)) {
      return {
        ok: false,
        status: res.status || 502,
        body: { error_code: "invalid_manual_response" },
      };
    }

    const echo = parseManualVerificationEcho(record);
    if (!echo) {
      return {
        ok: false,
        status: res.status || 502,
        body: { error_code: "invalid_manual_response" },
      };
    }

    const detail =
      typeof record.detail === "string" && record.detail.trim()
        ? record.detail.trim()
        : undefined;

    return {
      ok: true,
      referenceId,
      verdict: verdictRaw,
      rationaleKeys,
      headlineKey,
      heuristicScore,

      reputationOutcome:
        readString(record.reputation_outcome) ??
        readString(record.reputationOutcome),
      reputationFetchedAt: readOptionalStringRecord(
        record,
        "reputation_fetched_at",
        "reputationFetchedAt",
      ),
      dataFreshnessNoteKey:
        readString(record.data_freshness_note_key) ??
        readString(record.dataFreshnessNoteKey),
      permitFindingKey:
        readString(record.permit_finding_key) ??
        readString(record.permitFindingKey),

      echo,
      detail,
    };
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
  if (!base) {
    return {
      ok: false,
      status: 0,
      body: { error_code: "configuration_missing" },
    };
  }

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

    const raw = jsonBody as Record<string, unknown>;

    const ocrStatus =
      typeof raw.ocr_status === "string"
        ? raw.ocr_status
        : typeof raw.ocrStatus === "string"
          ? raw.ocrStatus
          : "";

    const ocrQualityHint =
      typeof raw.ocr_quality_hint === "string"
        ? raw.ocr_quality_hint
        : typeof raw.ocrQualityHint === "string"
          ? raw.ocrQualityHint
          : "";

    const nestedFields = raw.fields;
    const parsedFromNested =
      typeof nestedFields === "object" && nestedFields !== null
        ? parseManualVerificationEcho({ fields: nestedFields })
        : parseManualVerificationEcho(raw);

    const fieldsParsed =
      parsedFromNested ?? {
        developer: "",
        project: "",
        permit: "",
        address: "",
      };

    const preFrom = raw.manual_prefill ?? raw.manualPrefill;
    const parsedPref =
      typeof preFrom === "object" && preFrom !== null
        ? readEchoFields(preFrom as Record<string, unknown>)
        : null;

    const manualPrefill: Partial<ManualVerificationEcho> = {};

    const assign = (k: keyof ManualVerificationEcho) => {
      const fv = fieldsParsed[k];
      const pv = parsedPref?.[k];
      if (typeof fv === "string" && fv.trim()) {
        manualPrefill[k] = fv;
      }
      if (!(k in manualPrefill) && typeof pv === "string" && pv.trim()) {
        manualPrefill[k] = pv;
      }
    };
    assign("developer");
    assign("project");
    assign("permit");
    assign("address");

    const detail =
      typeof raw.detail === "string" && raw.detail.trim()
        ? raw.detail.trim()
        : undefined;

    return {
      ok: true,
      ocrStatus: ocrStatus || "failure",
      ocrQualityHint: ocrQualityHint || "low",
      fields: {
        developer: fieldsParsed.developer,
        project: fieldsParsed.project,
        permit: fieldsParsed.permit,
        address: fieldsParsed.address,
      },
      manualPrefill,
      detail,
    };
  } catch {
    clearTimeout(t);
    return { ok: false, status: 0, body: null };
  }
}

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
