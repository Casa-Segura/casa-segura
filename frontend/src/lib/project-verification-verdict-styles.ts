import type { ProjectVerificationVerdict } from "@/lib/project-verification-types";

export type VerdictVisualTone = {
  /** Banner frame: border + background only */
  container: string;
  /** Heading text color */
  title: string;
  /** Icon wells for non-color-only signaling */
  iconRing: string;
};

export function verdictVisualTone(
  verdict: ProjectVerificationVerdict,
): VerdictVisualTone {
  switch (verdict) {
    case "green":
      return {
        container:
          "border-verdict-green bg-verdict-green-bg border-2 [--verdict-accent:var(--color-verdict-green)]",
        title: "text-verdict-green",
        iconRing:
          "bg-white/85 text-verdict-green ring-2 ring-verdict-green/30",
      };
    case "red":
      return {
        container:
          "border-verdict-red bg-verdict-red-bg border-2 [--verdict-accent:var(--color-verdict-red)]",
        title: "text-verdict-red",
        iconRing: "bg-white/85 text-verdict-red ring-2 ring-verdict-red/30",
      };
    default:
      return {
        container:
          "border-verdict-yellow bg-verdict-yellow-bg border-2 [--verdict-accent:var(--color-verdict-yellow)]",
        title: "text-verdict-yellow",
        iconRing:
          "bg-white/85 text-verdict-yellow ring-2 ring-verdict-yellow/40",
      };
  }
}
