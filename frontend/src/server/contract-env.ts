/** Server-side env reads for Casa Segura API bridging (CASASEGURA_*). No NEXT_PUBLIC_* for privileged config.
 *
 * Vercel build requires a non-empty `CASASEGURA_API_BASE_URL`; when the API is not deployed, use the
 * documented `.invalid` placeholder with `CASASEGURA_UPLOAD_ENABLED=false` — see `frontend/README.md`.
 */

function parseCsvNumbers(raw: string | undefined): number[] {
  if (!raw) return [];
  return raw
    .split(",")
    .map((s) => Number(s.trim()))
    .filter((n) => Number.isFinite(n) && n > 0);
}

/** Base URL without trailing slash — `null` if unset. */
export function readContractApiBase(): string | null {
  const b = process.env.CASASEGURA_API_BASE_URL?.trim();
  if (!b) return null;
  return b.replace(/\/+$/, "");
}

/** Default follows PRD ingestion SLA wording + buffer (~90s). */
export function readSubmitTimeoutMs(): number {
  const raw = Number(process.env.CASASEGURA_UPLOAD_SUBMIT_TIMEOUT_MS);
  return Number.isFinite(raw) && raw >= 5_000 ? raw : 90_000;
}

/**
 * Total wall-clock polling budget after POST success.
 * Intended to cover ~90s+ pipeline under slow OCR per CS-296 BVA hints.
 */
export function readPollBudgetMs(): number {
  const raw = Number(process.env.CASASEGURA_UPLOAD_POLL_BUDGET_MS);
  return Number.isFinite(raw) && raw >= 10_000 ? raw : 120_000;
}

export function readPollBackoffMsSeries(): readonly number[] {
  const csv = parseCsvNumbers(process.env.CASASEGURA_UPLOAD_POLL_BACKOFF_MS);
  if (csv.length > 0) return csv as readonly number[];
  /** Documented backoff: starts at 1s, doubles-ish, capped at 5s. */
  return [1_000, 2_000, 5_000] as const;
}

/** Canonical Django upload path: POST `/api/v1/submissions/`. Override via env only if BE mounts elsewhere. */
export function readSubmitPath(): string {
  return process.env.CASASEGURA_CONTRACT_SUBMIT_PATH?.trim() || "/api/v1/submissions/";
}

/** Use `{{id}}` placeholder for submission UUID string. */
export function readSubmissionStatusTemplate(): string {
  return (
    process.env.CASASEGURA_CONTRACT_SUBMISSION_PATH_TEMPLATE?.trim() ||
    "/api/v1/submissions/{{id}}/"
  );
}

/** When `false`, we short-circuit with a deterministic UX message — useful ahead of rollout. */
export function readUploadEnabled(): boolean {
  return process.env.CASASEGURA_UPLOAD_ENABLED !== "false";
}

/**
 * Path template for the public HTML report (F7 `GET /r/{id}` style).
 * Placeholder `{{id}}` is replaced with `public_short_id` (URL-encoded).
 */
export function readPublicReportPathTemplate(): string {
  return process.env.CASASEGURA_PUBLIC_REPORT_PATH_TEMPLATE?.trim() || "/r/{{id}}";
}

/** Builds absolute report URL; `null` when API base is unset (CS-294 stub-friendly). */
export function buildPublicReportUrl(publicShortId: string): string | null {
  const base = readContractApiBase();
  if (!base) return null;
  const id = publicShortId.trim();
  if (!id) return null;
  const tail = readPublicReportPathTemplate().replace("{{id}}", encodeURIComponent(id));
  return `${base}${tail.startsWith("/") ? tail : `/${tail}`}`;
}
