/** Deep-link query contract for OCR-degraded manual handoff (CS-351 until CS-350 wiring). */

export const MANUAL_VERIFICATION_ROUTE = "/verificacion-proyecto/manual" as const;

export const MANUAL_HANDOFF_PREFILL_KEYS = [
  "developer",
  "project",
  "permit",
  "address",
] as const;

export type ManualPrefillField = (typeof MANUAL_HANDOFF_PREFILL_KEYS)[number];

/** Known entry reasons — safe in telemetry; extend when OCR enum lands (CS-350). */
export const MANUAL_HANDOFF_SOURCES = [
  "verification_hub",
  "photo_skip",
  "billboard_stub_continue",
  "ocr_failure",
  "ocr_low_confidence",
  "ocr_timeout",
] as const;

export type ManualHandoffSource = (typeof MANUAL_HANDOFF_SOURCES)[number];

export type ManualVerificationHandoffInput = {
  developer?: string;
  project?: string;
  permit?: string;
  address?: string;
  source?: ManualHandoffSource;
};

const MAX_PREFILL_CHARS = 240;

export type ManualVerificationHandoffPrefill = {
  developer?: string;
  project?: string;
  permit?: string;
  address?: string;
};

export type ParsedManualVerificationHandoff = {
  initialValues: ManualVerificationHandoffPrefill;
  source: ManualHandoffSource | undefined;
  hasPrefill: boolean;
};

export function clampHandoffField(value: string | undefined): string | undefined {
  const t = value?.trim();
  if (!t) return undefined;
  return t.slice(0, MAX_PREFILL_CHARS);
}

function isManualHandoffSource(raw: string): raw is ManualHandoffSource {
  return (MANUAL_HANDOFF_SOURCES as readonly string[]).includes(raw);
}

export function parseManualHandoffSource(
  raw: string | undefined,
): ManualHandoffSource | undefined {
  const t = raw?.trim();
  if (!t || !isManualHandoffSource(t)) return undefined;
  return t;
}

export function buildManualVerificationHandoffSearchParams(
  input: ManualVerificationHandoffInput,
): URLSearchParams {
  const p = new URLSearchParams();
  const developer = clampHandoffField(input.developer);
  const project = clampHandoffField(input.project);
  const permit = clampHandoffField(input.permit);
  const address = clampHandoffField(input.address);

  if (developer) p.set("developer", developer);
  if (project) p.set("project", project);
  if (permit) p.set("permit", permit);
  if (address) p.set("address", address);
  if (input.source) p.set("source", input.source);

  return p;
}

/** Path suitable for `<Link href={…}>` (no PII logged by this helper). */
export function buildManualVerificationHandoffPath(
  input: ManualVerificationHandoffInput,
): string {
  const qs = buildManualVerificationHandoffSearchParams(input).toString();
  return qs
    ? `${MANUAL_VERIFICATION_ROUTE}?${qs}`
    : MANUAL_VERIFICATION_ROUTE;
}

/** Parse App Router searchParams / plain records (multi-value keys use first entry). */
export function parseManualVerificationHandoffSearchParams(sp: {
  developer?: string | string[];
  project?: string | string[];
  permit?: string | string[];
  address?: string | string[];
  source?: string | string[];
}): ParsedManualVerificationHandoff {
  const pick = (k: keyof typeof sp): string | undefined => {
    const v = sp[k];
    const s = Array.isArray(v) ? v[0] : v;
    return clampHandoffField(typeof s === "string" ? s : undefined);
  };

  const initialValues: ManualVerificationHandoffPrefill = {
    developer: pick("developer"),
    project: pick("project"),
    permit: pick("permit"),
    address: pick("address"),
  };

  const sourceRaw = Array.isArray(sp.source) ? sp.source[0] : sp.source;
  const source = parseManualHandoffSource(sourceRaw);

  const hasPrefill =
    !!initialValues.developer ||
    !!initialValues.project ||
    !!initialValues.permit ||
    !!initialValues.address;

  return { initialValues, source, hasPrefill };
}

export function impliesOcrRecoverySource(
  source: ManualHandoffSource | undefined,
): boolean {
  if (!source) return false;
  return (
    source === "ocr_failure" ||
    source === "ocr_low_confidence" ||
    source === "ocr_timeout"
  );
}
