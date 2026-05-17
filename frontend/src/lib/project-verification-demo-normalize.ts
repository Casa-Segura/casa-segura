import {
  resolveProjectVerificationFreshness,
  resolveProjectVerificationHeadline,
  resolveProjectVerificationRationaleLines,
} from "./project-verification-copy";
import type { ProjectVerificationResultPreview } from "./project-verification-types";

function isVerdict(raw: unknown): raw is ProjectVerificationResultPreview["verdict"] {
  return raw === "green" || raw === "yellow" || raw === "red";
}

/**
 * Maps Django `GET .../demo-result/` JSON and key-based manual payloads into FE previews.
 */
export function normalizeProjectVerificationDemoResult(
  raw: unknown,
): ProjectVerificationResultPreview | null {
  if (typeof raw !== "object" || raw === null) return null;
  const o = raw as Record<string, unknown>;
  const verdict = o.verdict;
  if (!isVerdict(verdict)) return null;

  const rationaleKeysRaw = o.rationale_keys ?? o.rationaleKeys;
  const rationaleKeys = Array.isArray(rationaleKeysRaw)
    ? rationaleKeysRaw.filter((x): x is string => typeof x === "string")
    : null;

  const rationaleDirect = Array.isArray(o.rationale)
    ? o.rationale.filter((x): x is string => typeof x === "string")
    : [];

  const headlineKeyRaw =
    typeof o.headline_key === "string"
      ? o.headline_key.trim()
      : typeof o.headlineKey === "string"
        ? o.headlineKey.trim()
        : "";

  const headlineDirect =
    typeof o.headline === "string" && o.headline.trim()
      ? o.headline.trim()
      : "";

  const headline = headlineDirect
    ? headlineDirect
    : headlineKeyRaw
      ? resolveProjectVerificationHeadline(headlineKeyRaw)
      : "";

  const rationale =
    rationaleDirect.length && !rationaleKeys?.length
      ? rationaleDirect
      : rationaleKeys?.length
        ? resolveProjectVerificationRationaleLines(rationaleKeys)
        : rationaleDirect;

  const freshnessKeyRawSnake =
    typeof o.data_freshness_note_key === "string"
      ? o.data_freshness_note_key.trim()
      : "";

  const freshnessKeyRawCamel =
    typeof o.dataFreshnessNoteKey === "string"
      ? (o.dataFreshnessNoteKey as string).trim()
      : "";

  const freshnessKeyRaw = freshnessKeyRawSnake || freshnessKeyRawCamel;

  const dataFreshnessNoteDirectSnake =
    typeof o.data_freshness_note === "string"
      ? o.data_freshness_note.trim()
      : "";

  const dataFreshnessNoteDirectCamel =
    typeof o.dataFreshnessNote === "string"
      ? o.dataFreshnessNote.trim()
      : "";

  const dataFreshnessNoteDirect =
    dataFreshnessNoteDirectSnake || dataFreshnessNoteDirectCamel;

  const mappedFresh = freshnessKeyRaw
    ? resolveProjectVerificationFreshness(freshnessKeyRaw)
    : undefined;

  const dataFreshnessNote = dataFreshnessNoteDirect || mappedFresh;

  if (!headline.trim()) return null;

  return {
    verdict,
    headline: headline.trim(),
    rationale,
    ...(dataFreshnessNote ? { dataFreshnessNote } : {}),
  };
}
