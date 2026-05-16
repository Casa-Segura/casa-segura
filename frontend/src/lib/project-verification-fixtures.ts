import type {
  ProjectVerificationResultPreview,
  ProjectVerificationVerdict,
} from "./project-verification-types";

const FIXTURES: Record<
  ProjectVerificationVerdict,
  ProjectVerificationResultPreview
> = {
  green: {
    verdict: "green",
    headline: "Coincidencias alentadoras",
    rationale: [
      "El expediente declarado aparece en el catálogo de ejemplo con estado vigente.",
      "No encontramos inconsistencias obvias entre el nombre del proyecto y el desarrollador.",
    ],
    dataFreshnessNote: "Datos de reputación simulados al 15 may 2026 (stub).",
  },
  yellow: {
    verdict: "yellow",
    headline: "Revisá con calma",
    rationale: [
      "Hay coincidencia parcial: el permiso podría corresponder a una fase distinta.",
      "Te recomendamos confirmar en la municipalidad antes de tomar una decisión.",
    ],
    dataFreshnessNote: "Datos de reputación simulados al 15 may 2026 (stub).",
  },
  red: {
    verdict: "red",
    headline: "Riesgos detectados (demo)",
    rationale: [
      "No encontramos el permiso en el conjunto de prueba o el formato no coincide.",
      "Esto no bloquea el análisis de tu contrato en /subir.",
    ],
    dataFreshnessNote: "Datos de reputación simulados al 15 may 2026 (stub).",
  },
};

export function getProjectVerificationFixture(
  verdict: unknown,
): ProjectVerificationResultPreview {
  if (verdict === "green" || verdict === "yellow" || verdict === "red") {
    return FIXTURES[verdict];
  }
  return FIXTURES.yellow;
}
