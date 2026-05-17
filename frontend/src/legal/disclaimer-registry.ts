/**
 * CS-337 prep shim: single import surface for canon strings from `@/legal/disclaimer`.
 * Full registry + ESLint lint will replace this layering when the shared package lands.
 */
export {
  DISCLAIMER_EXTENDED_FOOTER,
  DISCLAIMER_GATE_LABEL,
  DISCLAIMER_ID,
  DISCLAIMER_SHORT,
  disclaimerCopy,
  type DisclaimerCopy,
} from "./disclaimer";
