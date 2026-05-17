import type { ProjectVerificationVerdict } from "@/lib/project-verification-types";
import { verdictVisualTone } from "@/lib/project-verification-verdict-styles";

/** Concatenated style tokens — snapshot guard for SSR / palettes per band (CS-355). */
export function getProjectVerificationVerdictBannerFingerprint(
  verdict: ProjectVerificationVerdict,
): string {
  const tone = verdictVisualTone(verdict);
  return [tone.container, tone.iconRing, tone.title].join("|");
}

export function projectVerificationVerdictAriaLabelForBand(
  verdict: ProjectVerificationVerdict,
): string {
  switch (verdict) {
    case "green":
      return "Señal alentadora: banda verde.";
    case "red":
      return "Señal de precaución: banda roja.";
    default:
      return "Señal neutra mixta: banda amarilla.";
  }
}
