/**
 * Cite-or-stay-silent gate for cosine similarity scores (0–1), aligned with
 * `backend/corpus/application/retrieval.py` (`similarity >= threshold`).
 *
 * Boundary intent (nominal threshold 0.65): scores just below 0.65 stay
 * silent; scores at/above qualify for citation (`STATUS_RECONCILIATION` BVA —
 * exemplar deltas 0.649 vs 0.651).
 */
export function legalChunkIncludedBySimilarity(
  cosineSimilarity: number,
  threshold: number,
): boolean {
  return cosineSimilarity >= threshold;
}
