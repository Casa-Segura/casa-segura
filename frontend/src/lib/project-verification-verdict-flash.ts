/**
 * Sessionless resultado handoff via short-lived HTTP-only cookie (EPIC-12 / CS-355).
 * Payload is key-based only (no free-text OCR or addresses).
 */

import type {
  ProjectVerificationVerdict,
} from "@/lib/project-verification-types";

export const PROJECT_VERIFICATION_VERDICT_FLASH_COOKIE =
  "cs_pv_verdict_flash_v1";

export const PROJECT_VERIFICATION_VERDICT_FLASH_MAX_AGE_S = 120;

export type ProjectVerificationVerdictFlashV1 = {
  readonly v: 1;
  readonly verdict: ProjectVerificationVerdict;
  readonly headlineKey: string;
  readonly rationaleKeys: readonly string[];
  readonly dataFreshnessNoteKey?: string | null;
  readonly referenceId?: string;
  readonly heuristicScore?: number;
  readonly reputationOutcome?: string;
  readonly reputationFetchedAt?: string | null;
  readonly permitFindingKey?: string;
};

function isVerdict(raw: unknown): raw is ProjectVerificationVerdict {
  return raw === "green" || raw === "yellow" || raw === "red";
}

function isStringArray(raw: unknown): raw is string[] {
  return Array.isArray(raw) && raw.every((x) => typeof x === "string");
}

export function serializeProjectVerificationVerdictFlash(
  payload: Omit<ProjectVerificationVerdictFlashV1, "v">,
): string {
  const body: ProjectVerificationVerdictFlashV1 = {
    v: 1,
    ...payload,
  };
  const json = JSON.stringify(body);
  return Buffer.from(json, "utf8").toString("base64url");
}

export function parseProjectVerificationVerdictFlashCookie(
  raw: string | undefined,
): ProjectVerificationVerdictFlashV1 | null {
  if (!raw?.trim()) return null;
  try {
    const json = Buffer.from(raw.trim(), "base64url").toString("utf8");
    const o = JSON.parse(json) as unknown;
    if (typeof o !== "object" || o === null) return null;
    const rec = o as Record<string, unknown>;
    if (rec.v !== 1) return null;
    if (!isVerdict(rec.verdict)) return null;
    const headlineKey =
      typeof rec.headline_key === "string"
        ? rec.headline_key
        : typeof rec.headlineKey === "string"
          ? rec.headlineKey
          : "";
    const rationaleRaw = rec.rationale_keys ?? rec.rationaleKeys ?? [];
    if (!isStringArray(rationaleRaw)) return null;

    const dataFreshnessNoteKey =
      rec.dataFreshnessNoteKey === null ||
      typeof rec.dataFreshnessNoteKey === "string"
        ? rec.dataFreshnessNoteKey
        : rec.data_freshness_note_key === null ||
            typeof rec.data_freshness_note_key === "string"
          ? (rec.data_freshness_note_key as string | null)
          : undefined;

    const referenceId =
      typeof rec.reference_id === "string"
        ? rec.reference_id
        : typeof rec.referenceId === "string"
          ? rec.referenceId
          : undefined;

    const reputationOutcome =
      typeof rec.reputation_outcome === "string"
        ? rec.reputation_outcome
        : typeof rec.reputationOutcome === "string"
          ? rec.reputationOutcome
          : undefined;

    const reputationFetchedAt =
      rec.reputation_fetched_at === null ||
      typeof rec.reputation_fetched_at === "string"
        ? (rec.reputation_fetched_at as string | null)
        : rec.reputationFetchedAt === null ||
            typeof rec.reputationFetchedAt === "string"
          ? (rec.reputationFetchedAt as string | null)
          : undefined;

    const permitFindingKey =
      typeof rec.permit_finding_key === "string"
        ? rec.permit_finding_key
        : typeof rec.permitFindingKey === "string"
          ? rec.permitFindingKey
          : undefined;

    const heuristicScore = Number(rec.heuristic_score ?? rec.heuristicScore);

    return {
      v: 1,
      verdict: rec.verdict as ProjectVerificationVerdict,
      headlineKey: headlineKey.trim(),
      rationaleKeys: rationaleRaw,
      dataFreshnessNoteKey,
      referenceId,
      reputationOutcome,
      reputationFetchedAt,
      permitFindingKey,
      heuristicScore: Number.isFinite(heuristicScore)
        ? heuristicScore
        : undefined,
    };
  } catch {
    return null;
  }
}
