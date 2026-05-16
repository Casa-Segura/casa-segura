/** Verdict band for project verification results (shell / fixtures until CS-354 DTO lands). */
export type ProjectVerificationVerdict = "green" | "yellow" | "red";

export type ProjectVerificationResultPreview = {
  verdict: ProjectVerificationVerdict;
  headline: string;
  rationale: string[];
  dataFreshnessNote?: string;
};
