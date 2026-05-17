"use client";

import { CheckCircle, Warning, WarningOctagon } from "@phosphor-icons/react";
import type { ProjectVerificationVerdict } from "@/lib/project-verification-types";
import { projectVerificationVerdictAriaLabelForBand } from "@/lib/project-verification-verdict-presenter";

const iconProps = {
  size: 44 as const,
  weight: "duotone" as const,
};

export function ProjectVerificationVerdictIcon({
  verdict,
}: Readonly<{ verdict: ProjectVerificationVerdict }>) {
  const label = projectVerificationVerdictAriaLabelForBand(verdict);
  switch (verdict) {
    case "green":
      return (
        <span role="img" aria-label={label} className="inline-flex shrink-0">
          <CheckCircle {...iconProps} aria-hidden />
        </span>
      );
    case "red":
      return (
        <span role="img" aria-label={label} className="inline-flex shrink-0">
          <WarningOctagon {...iconProps} aria-hidden />
        </span>
      );
    default:
      return (
        <span role="img" aria-label={label} className="inline-flex shrink-0">
          <Warning {...iconProps} aria-hidden />
        </span>
      );
  }
}
