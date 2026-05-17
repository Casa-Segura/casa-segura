/**
 * Stable Spanish copy for billboard / verdict machine keys (CS-355).
 * Legal short line stays in `@/legal/disclaimer-registry`.
 */

const HEADLINE: Record<string, string> = {
  "pv.headline.green": "Coincidencias alentadoras",
  "pv.headline.yellow": "Revisá con calma",
  "pv.headline.red": "Riesgos o dudas importantes",
  "pv.headline.green.demo": "Demo en verde (ejemplo)",
  "pv.headline.yellow.demo": "Demo en amarillo (ejemplo)",
  "pv.headline.red.demo": "Demo en rojo (ejemplo)",
};

const FRESHNESS: Record<string, string> = {
  "pv.freshness.demo":
    "Texto demo ilustrativo, sin corroboración ante registros públicos.",
  "pv.reputation.freshness.stub": "Sin fuente reputacional configurada.",
  "pv.reputation.timeout_note": "Señales adicionales no llegaron a tiempo.",
};

const RATIONALE: Record<string, string> = {
  "pv.reputation.skipped_disabled":
    "No hay fuente reputacional activa para esta instalación.",

  "pv.reputation.evidence_positive":
    "Hallazgos favorables muy acotados (no equivalen a validez legal).",

  "pv.reputation.evidence_negative":
    "Hallazgos desfavorables muy acotados (solo pistas, no fallos formales).",

  "pv.reputation.degraded":
    "No pudimos ampliar con señales externas; usamos lo declarado.",

  "pv.ocr.low_confidence_penalty":
    "La foto se leyó con poca seguridad.",

  "pv.ocr.medium_confidence_penalty":
    "La foto se leyó con seguridad media.",

  "pv.policy.cap_green_unknown_permit":
    "Con permiso poco claro no mostramos un veredicto completamente favorable.",

  "pv.override.suspicious_permit_negative_rep":
    "Formato débil más señales externas adversas sugieren mayor cautela.",
};

export function resolveProjectVerificationHeadline(key: string | undefined): string {
  const k = key?.trim();
  if (!k) return "Resultado de verificación";
  return HEADLINE[k] ?? "Resultado de verificación";
}

export function resolveProjectVerificationFreshness(
  key: string | undefined,
): string | undefined {
  const k = key?.trim();
  if (!k) return undefined;
  return FRESHNESS[k];
}

function rationaleLine(key: string): string {
  if (RATIONALE[key]) return RATIONALE[key];

  if (key.startsWith("permit.format_ok."))
    return "El permiso se parece a plantillas típicas (chequeo sólo orientativo).";

  if (key.startsWith("permit.format_unknown."))
    return "No encontramos coincidencias claras con patrones conocidos.";

  if (key.startsWith("permit.format_suspicious."))
    return "El formato del permiso es raro respecto de plantillas conocidas.";

  return "Señal técnica registrada sin exponer detalles.";
}

export function resolveProjectVerificationRationaleLines(
  keys: string[],
): string[] {
  const out: string[] = [];
  for (const raw of keys) {
    if (!raw.startsWith("pv.headline.")) {
      const line = rationaleLine(raw);
      if (line && !out.includes(line)) out.push(line);
    }
  }
  return out;
}
