"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { CheckCircle, DownloadSimple, ShareNetwork } from "@phosphor-icons/react";
import {
  BrandMark,
  CasaButton,
  CasaLinkButton,
  DocumentPreview,
  FindingCard,
  LegalSummary,
  ProgressTimeline,
  SkeletonBlock,
  StatusPill,
  cx,
  type ProgressStep,
} from "@/components/casa-ui";

type WorkbenchMode = "loading" | "complete" | "preview";

const defaultSteps: ProgressStep[] = [
  {
    id: "upload",
    label: "Contrato recibido",
    detail: "Guardamos el archivo sólo para este análisis.",
    state: "done",
  },
  {
    id: "ocr",
    label: "Extrayendo texto",
    detail: "OCR y lectura del PDF en progreso.",
    state: "done",
  },
  {
    id: "criteria",
    label: "Analizando 38 criterios",
    detail: "Comparando cláusulas contra señales de riesgo.",
    state: "active",
  },
  {
    id: "report",
    label: "Generando reporte",
    detail: "Preparando resumen, citas y recomendaciones.",
    state: "pending",
  },
  {
    id: "delivery",
    label: "Confirmando entrega",
    detail: "PDF, SMS o enlace web según tu selección.",
    state: "pending",
  },
];

const completedSteps: ProgressStep[] = defaultSteps.map((step) => ({
  ...step,
  state: "done",
}));

export function AnalysisWorkbench({
  mode = "preview",
  publicShortId,
}: {
  mode?: WorkbenchMode;
  publicShortId?: string;
}) {
  const complete = mode === "complete";
  const loading = mode === "loading";
  const preview = !loading && !complete;
  const showOutcomeActions = complete;
  const reduceMotion = useReducedMotion();
  const enter = reduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: 10 };
  const leave = reduceMotion ? { opacity: 1, y: 0 } : { opacity: 0, y: -8 };

  return (
    <section
      className={cx(
        "hidden overflow-hidden rounded-[var(--radius-panel)] border border-border bg-surface-muted shadow-[var(--shadow-panel)] lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]",
        preview ? "min-h-[520px]" : "min-h-[760px]",
      )}
      aria-label="Mesa de análisis del contrato"
    >
      <div className="flex min-h-0 min-w-0 flex-col border-r border-border bg-surface">
        <header className="flex min-h-[52px] items-center justify-between border-b border-border px-5">
          <BrandMark />
          <span className="min-w-0 truncate text-xs font-medium text-text-secondary">
            {preview
              ? "Sin documento aún"
              : loading
                ? "Leyendo tu contrato…"
                : "Contrato_Venta_Rivas.pdf"}
          </span>
        </header>
        <div className="flex flex-1 items-center justify-center bg-surface-muted p-6">
          <DocumentPreview
            phase={loading ? "scanning" : complete ? "result" : "idle"}
            className="w-full max-w-[560px]"
          />
        </div>
      </div>

      <aside className="flex min-h-0 min-w-0 flex-col bg-surface-muted">
        <header className="flex min-h-[52px] items-center justify-between border-b border-border bg-surface px-5">
          {loading ? (
            <StatusPill tone="yellow" pulse>
              Analizando criterios
            </StatusPill>
          ) : complete ? (
            <StatusPill tone="green">Análisis completado</StatusPill>
          ) : (
            <StatusPill tone="accent">Vista previa</StatusPill>
          )}
          {publicShortId ? (
            <span className="font-mono text-xs text-text-secondary">
              {publicShortId}
            </span>
          ) : null}
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          <AnimatePresence mode="popLayout">
            {loading ? (
              <motion.div
                key="loading"
                initial={enter}
                animate={{ opacity: 1, y: 0 }}
                exit={leave}
                transition={{ type: "spring", stiffness: 130, damping: 22 }}
                className="flex flex-col gap-5"
              >
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
                    En vivo
                  </p>
                  <h2 className="mt-2 text-xl font-semibold tracking-tight text-text-primary">
                    Revisando tu contrato
                  </h2>
                  <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                    Estamos leyendo el documento, detectando cláusulas y preparando
                    las áreas de interés para el reporte final.
                  </p>
                </div>
                <ProgressTimeline steps={defaultSteps} progress={58} />
                <SkeletonPanel />
              </motion.div>
            ) : complete ? (
              <motion.div
                key="complete"
                initial={enter}
                animate={{ opacity: 1, y: 0 }}
                exit={leave}
                transition={{ type: "spring", stiffness: 130, damping: 22 }}
                className="flex flex-col gap-5"
              >
                <ScoreSummary />
                <ProgressTimeline steps={completedSteps} progress={100} />
                <LegalSummary>
                  Tus alertas se basan en la Ley de Inquilinato y el Código
                  Civil. Usá este resultado como preparación para conversar con
                  un abogado antes de firmar.
                </LegalSummary>
                <div className="flex flex-col gap-3">
                  <FindingCard
                    tone="red"
                    title="Penalización por mora desproporcionada"
                    body="La cláusula permite cargos acumulados sin límite claro. Pedí un tope por escrito."
                    citation="Código Civil · Art. 1605"
                  />
                  <FindingCard
                    tone="yellow"
                    title="Plazo de entrega ambiguo"
                    body="El contrato habla de fechas estimadas, pero no define compensación por retrasos."
                    citation="Ley de Inquilinato · Art. 4"
                  />
                  <FindingCard
                    tone="green"
                    title="Identificación del inmueble completa"
                    body="La dirección, matrícula y datos del proyecto aparecen de forma consistente."
                  />
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="preview"
                initial={enter}
                animate={{ opacity: 1, y: 0 }}
                exit={leave}
                transition={{ type: "spring", stiffness: 130, damping: 22 }}
              >
                <PreviewCompanionPanel />
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {showOutcomeActions ? (
          <footer className="border-t border-border bg-surface p-4">
            <div className="grid grid-cols-2 gap-3">
              <CasaButton variant="secondary" className="text-sm">
                <ShareNetwork size={16} aria-hidden />
                Compartir
              </CasaButton>
              <CasaLinkButton href="/subir" className="text-sm">
                <DownloadSimple size={16} aria-hidden />
                Nuevo análisis
              </CasaLinkButton>
            </div>
          </footer>
        ) : null}
      </aside>
    </section>
  );
}

function PreviewCompanionPanel() {
  const bullets = [
    "Un resumen con puntaje orientativo y mensaje claro.",
    "Pasos del análisis (lectura, criterios, reporte).",
    "Hallazgos por severidad: crítico, atención y correcto.",
  ];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
          Antes de enviar
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight text-text-primary">
          Así se verá tu informe en escritorio
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-text-secondary">
          Esta columna se llena cuando el análisis corre de verdad: primero verás
          el progreso y placeholders animados, después el resultado completo.
          Todavía no hay datos de tu contrato.
        </p>
      </div>
      <section
        className="rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-[var(--shadow-soft)]"
        aria-label="Qué incluye el informe"
      >
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-text-secondary">
          Incluye
        </p>
        <ul className="mt-3 flex flex-col gap-3 text-sm text-text-primary">
          {bullets.map((line) => (
            <li key={line} className="flex gap-3">
              <CheckCircle
                size={20}
                className="mt-0.5 shrink-0 text-accent"
                weight="fill"
                aria-hidden
              />
              <span className="leading-relaxed">{line}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function SkeletonPanel() {
  return (
    <section className="rounded-[var(--radius-card)] border border-border bg-surface p-4">
      <div className="mb-4 flex items-center justify-between">
        <SkeletonBlock className="h-3 w-32" label="Cargando sección" />
        <SkeletonBlock className="h-3 w-16" label="Cargando conteo" />
      </div>
      <div className="flex flex-col gap-3">
        <SkeletonBlock className="h-14 w-full" label="Cargando hallazgo" />
        <SkeletonBlock className="h-14 w-full" label="Cargando hallazgo" />
        <SkeletonBlock className="h-14 w-10/12" label="Cargando hallazgo" />
      </div>
    </section>
  );
}

function ScoreSummary() {
  return (
    <section className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-[var(--shadow-soft)]">
      <div className="flex items-center gap-4">
        <div className="flex size-16 shrink-0 items-center justify-center rounded-full border-4 border-verdict-green bg-verdict-green-bg font-mono text-lg font-bold text-verdict-green">
          74
        </div>
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            Resultado
          </p>
          <h2 className="mt-1 text-lg font-semibold text-text-primary">
            Contrato aceptable con 3 puntos críticos
          </h2>
          <p className="mt-1 text-sm leading-relaxed text-text-secondary">
            Revisá lo rojo antes de firmar y pedí aclaración por escrito.
          </p>
        </div>
      </div>
    </section>
  );
}
