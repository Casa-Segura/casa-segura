"use client";

import { useEffect, useState } from "react";
import {
  ANALYSIS_LOADING_LINES,
  ANALYSIS_LOADING_LONG_WAIT_LINE,
  ANALYSIS_LOADING_LONG_WAIT_THRESHOLD_MS,
  ANALYSIS_LOADING_ROTATION_MS,
} from "@/domain/analysis-loading-copy";

/**
 * CS-293 — rotating tú reassurance + busy indicator; aria-live polite; wall-clock cadence.
 * Mount only while the server action runs; parent remounts with a fresh key per submission so timers reset cleanly.
 */
export function ContractAnalysisLoadingPanel() {
  const [elapsedMs, setElapsedMs] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => setReducedMotion(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    const start = Date.now();
    const id = window.setInterval(() => {
      setElapsedMs(Date.now() - start);
    }, 1_000);
    return () => window.clearInterval(id);
  }, []);

  const rotationIndex =
    Math.floor(elapsedMs / ANALYSIS_LOADING_ROTATION_MS) % ANALYSIS_LOADING_LINES.length;
  const longWait = elapsedMs >= ANALYSIS_LOADING_LONG_WAIT_THRESHOLD_MS;
  const line = longWait
    ? ANALYSIS_LOADING_LONG_WAIT_LINE
    : (ANALYSIS_LOADING_LINES[rotationIndex] ?? "");

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-text-primary/40 p-4 backdrop-blur-[2px] sm:items-center"
      aria-busy="true"
    >
      <div className="flex w-full max-w-[480px] flex-col gap-4 rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-lg">
        <div className="flex items-start gap-4">
          <div
            className="mt-0.5 size-10 shrink-0 rounded-full border-2 border-accent border-t-transparent motion-safe:animate-spin motion-reduce:animate-none"
            aria-hidden
          />
          <div className="min-w-0 flex-1">
            <p className="text-base font-semibold text-text-primary">Analizando tu contrato</p>
            <p
              className="mt-2 text-sm leading-relaxed text-text-secondary"
              key={longWait ? "long" : `line-${rotationIndex}`}
              aria-live="polite"
              aria-atomic="true"
            >
              {line}
            </p>
          </div>
        </div>
        {reducedMotion ? (
          <p className="text-xs text-text-secondary">Preferencias de movimiento reducido activas.</p>
        ) : null}
      </div>
    </div>
  );
}
