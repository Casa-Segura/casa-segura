import type { ProgressStep } from "@/components/casa-ui";
import { ANALYSIS_LOADING_LONG_WAIT_THRESHOLD_MS } from "@/domain/analysis-loading-copy";

/**
 * Wall-clock simulated progress while the upload server action runs (CS-293).
 * Mirrors the modal; not tied to backend pipeline milestones.
 */
export function progressForElapsed(elapsedMs: number): number {
  if (elapsedMs < 4_000) return 18;
  if (elapsedMs < 12_000) return 40;
  if (elapsedMs < 28_000) return 58;
  if (elapsedMs < 50_000) return 76;
  if (elapsedMs < ANALYSIS_LOADING_LONG_WAIT_THRESHOLD_MS) return 88;
  return 92;
}

function stepStatesFromProgress(
  progress: number,
): Record<string, ProgressStep["state"]> {
  return {
    upload: "done",
    ocr: progress >= 40 ? "done" : "active",
    criteria: progress >= 76 ? "done" : progress >= 40 ? "active" : "pending",
    report: progress >= 88 ? "active" : "pending",
    delivery: "pending",
  };
}

export function withAnalysisLoadingProgress(
  templates: readonly Pick<ProgressStep, "id" | "label" | "detail">[],
  progress: number,
): ProgressStep[] {
  const states = stepStatesFromProgress(progress);
  return templates.map((t) => ({
    ...t,
    state: states[t.id] ?? "pending",
  }));
}
