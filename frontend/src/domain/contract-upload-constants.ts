/**
 * Limits aligned with PRD_F1_INGESTA_Y_OCR (supersedes older UI prose).
 * Mirrors CS-059 / CS-291 acceptance criteria defaults.
 */

export const CONTRACT_MAX_FILE_BYTES = 15 * 1024 * 1024; // 15 MB default per file

export const CONTRACT_MAX_TOTAL_BYTES = 100 * 1024 * 1024; // PRD §BR total cap

/** Per-submission count cap (DOMAIN_MODEL §4.1 / CS-050). */
export const CONTRACT_MAX_FILE_COUNT = 50;

/** Accept attribute + client validation (lowercase MIME). */
export const CONTRACT_ACCEPTABLE_MIME_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/heic",
  "image/heif",
  "image/webp",
] as const;

export const CONTRACT_ACCEPTABLE_EXTENSIONS = new Set([
  "pdf",
  "jpg",
  "jpeg",
  "png",
  "heic",
  "webp",
]);
