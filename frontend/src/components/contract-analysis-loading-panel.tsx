"use client";

import { useEffect, useState } from "react";
import {
  ANALYSIS_LOADING_LINES,
  ANALYSIS_LOADING_LONG_WAIT_LINE,
  ANALYSIS_LOADING_LONG_WAIT_THRESHOLD_MS,
  ANALYSIS_LOADING_ROTATION_MS,
} from "@/domain/analysis-loading-copy";
import {
  BrandMark,
  ProgressTimeline,
  SkeletonBlock,
  StatusPill,
  type ProgressStep,
} from "@/components/casa-ui";

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
    Math.floor(elapsedMs / ANALYSIS_LOADING_ROTATION_MS) %
    ANALYSIS_LOADING_LINES.length;
  const longWait = elapsedMs >= ANALYSIS_LOADING_LONG_WAIT_THRESHOLD_MS;
  const line = longWait
    ? ANALYSIS_LOADING_LONG_WAIT_LINE
    : (ANALYSIS_LOADING_LINES[rotationIndex] ?? "");
  const progress = progressForElapsed(elapsedMs);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-text-primary/45 p-4 backdrop-blur-[3px] sm:items-center"
      aria-busy="true"
    >
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="flex max-h-[88dvh] w-full max-w-[520px] flex-col overflow-y-auto rounded-[var(--radius-panel)] border border-border bg-surface p-5 shadow-[var(--shadow-panel)] sm:p-6"
      >
        <div className="flex items-center justify-between gap-4">
          <BrandMark />
          <StatusPill tone="yellow" pulse={!reducedMotion}>
            En proceso
          </StatusPill>
        </div>

        <div className="mt-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            Análisis legal
          </p>
          <h2 className="mt-2 text-balance text-xl font-semibold tracking-tight text-text-primary">
            Analizando tu contrato
          </h2>
          <p
            className="mt-2 text-sm leading-relaxed text-text-secondary"
            key={longWait ? "long" : `line-${rotationIndex}`}
          >
            {line}
          </p>
        </div>

        <div className="mt-5">
          <ProgressTimeline
            steps={buildLoadingSteps(progress)}
            progress={progress}
          />
        </div>

        <div className="mt-5 rounded-[var(--radius-card)] border border-border bg-surface-subtle p-4">
          <div className="mb-4 flex items-center justify-between">
            <SkeletonBlock className="h-3 w-36" label="Preparando hallazgos" />
            <SkeletonBlock className="h-3 w-14" label="Preparando conteo" />
          </div>
          <div className="flex flex-col gap-3">
            <SkeletonBlock
              className="h-12 w-full"
              label="Hallazgo en revisión"
            />
            <SkeletonBlock
              className="h-12 w-11/12"
              label="Hallazgo en revisión"
            />
            <SkeletonBlock
              className="h-12 w-10/12"
              label="Hallazgo en revisión"
            />
          </div>
        </div>

        {reducedMotion ? (
          <p className="mt-4 text-xs text-text-secondary">
            Preferencias de movimiento reducido activas.
          </p>
        ) : null}
      </div>
    </div>
  );
}

function progressForElapsed(elapsedMs: number): number {
  if (elapsedMs < 4_000) return 18;
  if (elapsedMs < 12_000) return 40;
  if (elapsedMs < 28_000) return 58;
  if (elapsedMs < 50_000) return 76;
  if (elapsedMs < ANALYSIS_LOADING_LONG_WAIT_THRESHOLD_MS) return 88;
  return 92;
}

function buildLoadingSteps(progress: number): ProgressStep[] {
  return [
    {
      id: "upload",
      label: "Contrato recibido",
      detail: "Validamos formato, tamaño y consentimiento.",
      state: "done",
    },
    {
      id: "ocr",
      label: "Extrayendo texto del contrato",
      detail: "OCR y lectura del PDF en progreso.",
      state: progress >= 40 ? "done" : "active",
    },
    {
      id: "criteria",
      label: "Analizando 38 criterios",
      detail: "Detectamos cláusulas y áreas de interés.",
      state: progress >= 76 ? "done" : progress >= 40 ? "active" : "pending",
    },
    {
      id: "report",
      label: "Generando reporte PDF",
      detail: "Ordenamos hallazgos, citas y recomendaciones.",
      state: progress >= 88 ? "active" : "pending",
    },
    {
      id: "delivery",
      label: "Preparando entrega",
      detail: "Confirmamos el canal que elegiste.",
      state: "pending",
    },
  ];
}
