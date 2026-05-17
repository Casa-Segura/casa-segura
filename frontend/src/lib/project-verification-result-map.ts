import {
  resolveProjectVerificationFreshness,
  resolveProjectVerificationHeadline,
  resolveProjectVerificationRationaleLines,
} from "@/lib/project-verification-copy";
import type { ProjectVerificationVerdictFlashV1 } from "@/lib/project-verification-verdict-flash";
import type { ProjectVerificationResultPreview } from "@/lib/project-verification-types";

export function projectVerificationPreviewFromVerdictFlash(
  flash: ProjectVerificationVerdictFlashV1,
): ProjectVerificationResultPreview {
  const headline = resolveProjectVerificationHeadline(flash.headlineKey);
  const rationale = resolveProjectVerificationRationaleLines([
    ...flash.rationaleKeys,
  ]);

  const resolvedFresh =
    resolveProjectVerificationFreshness(
      flash.dataFreshnessNoteKey ?? undefined,
    ) ?? undefined;

  return {
    verdict: flash.verdict,
    headline,
    rationale,
    referenceId: flash.referenceId,
    ...(resolvedFresh ? { dataFreshnessNote: resolvedFresh } : {}),
  };
}
