/**
 * Canonical disclaimer copy (BR-07 / F1 US-01). CS-297 single source:
 * import constants from this module — do not duplicate the Spanish literal elsewhere in `frontend/src`.
 */
export const DISCLAIMER_ID = "cs.disclaimer.short" as const;

/** BR-07 exact wording — Unicode í (U+00ED) required */
export const DISCLAIMER_SHORT = "Esto no es asesoría legal" as const;

/** Footer / muted surfaces: clause after the highlighted short disclaimer */
export const DISCLAIMER_EXTENDED_FOOTER =
  "Casa Segura te ayuda a entender puntos comunes en contratos inmobiliarios; no sustituye la revisión de un abogado." as const;

/** Checkbox label (gate): consequence for SR + legal acknowledgement */
export const DISCLAIMER_GATE_LABEL =
  "Confirmo que entiendo que esto no es asesoría legal y que Casa Segura no sustituye la revisión de un abogado." as const;

export type DisclaimerCopy = {
  id: typeof DISCLAIMER_ID;
  short: typeof DISCLAIMER_SHORT;
  extendedFooter: typeof DISCLAIMER_EXTENDED_FOOTER;
  gateLabel: typeof DISCLAIMER_GATE_LABEL;
};

export const disclaimerCopy: DisclaimerCopy = {
  id: DISCLAIMER_ID,
  short: DISCLAIMER_SHORT,
  extendedFooter: DISCLAIMER_EXTENDED_FOOTER,
  gateLabel: DISCLAIMER_GATE_LABEL,
};
