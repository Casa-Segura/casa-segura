/**
 * Canonical legal disclaimer copy (BR-07 / F1). CS-297 will centralize
 * all surfaces; import this module instead of duplicating the string.
 */
export const DISCLAIMER_LEGAL_SHORT = "Esto no es asesoría legal" as const;

export type DisclaimerCopy = {
  short: typeof DISCLAIMER_LEGAL_SHORT;
};

export const disclaimerCopy: DisclaimerCopy = {
  short: DISCLAIMER_LEGAL_SHORT,
};
