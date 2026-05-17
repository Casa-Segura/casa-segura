export type ProjectVerificationVerdict = "green" | "yellow" | "red";

/** User-facing resultado payload (localized copy resolved on the FE). */
export type ProjectVerificationResultPreview = {
  verdict: ProjectVerificationVerdict;
  headline: string;
  rationale: string[];
  dataFreshnessNote?: string;
  referenceId?: string;
};
