import type { ProjectVerificationResultPreview } from "./project-verification-types";

/** Maps Django stub `GET .../demo-result/` JSON (snake_case) to FE preview types. */
export function normalizeProjectVerificationDemoResult(
  raw: unknown,
): ProjectVerificationResultPreview | null {
  if (typeof raw !== "object" || raw === null) return null;
  const o = raw as Record<string, unknown>;
  const verdict = o.verdict;
  if (verdict !== "green" && verdict !== "yellow" && verdict !== "red")
    return null;

  const headline = typeof o.headline === "string" ? o.headline.trim() : "";
  if (!headline) return null;

  const rationaleRaw = o.rationale;
  const rationale = Array.isArray(rationaleRaw)
    ? rationaleRaw.filter((x): x is string => typeof x === "string")
    : [];

  const dataFreshnessNote =
    typeof o.data_freshness_note === "string"
      ? o.data_freshness_note.trim()
      : typeof o.dataFreshnessNote === "string"
        ? o.dataFreshnessNote.trim()
        : undefined;

  return {
    verdict,
    headline,
    rationale,
    ...(dataFreshnessNote ? { dataFreshnessNote } : {}),
  };
}
