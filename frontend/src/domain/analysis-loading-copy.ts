/**
 * CS-293 — copy + timing for rotating reassurance while the upload+poll server action runs.
 * Rotation advances on wall-clock (setInterval), not on poll responses.
 */

/** Midpoint of the 4–6s AC band */
export const ANALYSIS_LOADING_ROTATION_MS = 5_000;

/**
 * Calmer long-wait line appears after this wall threshold (BVA: approach ~90s SLA).
 * Documented here as 60s per CS-293 ticket boundary table.
 */
export const ANALYSIS_LOADING_LONG_WAIT_THRESHOLD_MS = 60_000;

export const ANALYSIS_LOADING_LINES: readonly string[] = [
  "Estamos leyendo las páginas que subiste; esto puede tardar un poco.",
  "Comparamos cláusulas con lo que suele verse en compraventa de vivienda.",
  "Si el PDF es escaneado, el OCR necesita unos segundos extra.",
  "No cierres esta pestaña; te avisaremos en cuanto haya un resultado claro.",
];

export const ANALYSIS_LOADING_LONG_WAIT_LINE =
  "Sigue en proceso; los análisis largos pueden acercarse al minuto y medio. Gracias por esperar.";
