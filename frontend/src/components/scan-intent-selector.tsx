"use client";

import { Camera, FileText, ShieldCheck } from "@phosphor-icons/react";
import { StepPill, cx, focusRing } from "@/components/casa-ui";

export type ScanIntent = "contract" | "billboard";

type IntentOption = {
  id: ScanIntent;
  title: string;
  description: string;
  details: string;
  action: string;
  icon: typeof FileText;
};

const OPTIONS: IntentOption[] = [
  {
    id: "contract",
    title: "Contrato de compra o alquiler",
    description:
      "Subí PDF o fotos del contrato para revisar cláusulas, riesgos y base legal.",
    details: "Ideal antes de firmar o pedir cambios por escrito.",
    action: "Revisar contrato",
    icon: FileText,
  },
  {
    id: "billboard",
    title: "Valla publicitaria / proyecto",
    description:
      "Tomá o subí una foto de la valla para iniciar verificación del proyecto.",
    details: "Útil cuando querés validar señales visibles antes de avanzar.",
    action: "Revisar valla",
    icon: Camera,
  },
];

export function ScanIntentSelector({
  onSelect,
}: {
  onSelect: (intent: ScanIntent) => void;
}) {
  return (
    <section
      aria-labelledby="scan-intent-heading"
      className="grid gap-6 lg:grid-cols-[minmax(0,0.92fr)_minmax(360px,0.68fr)] lg:items-start"
    >
      <div className="rounded-[var(--radius-panel)] border border-border bg-surface p-5 shadow-[var(--shadow-soft)] sm:p-6">
        <StepPill>Paso 1 de 4 · Elegir revisión</StepPill>
        <h1
          id="scan-intent-heading"
          className="mt-4 text-balance text-3xl font-semibold tracking-tight text-text-primary sm:text-4xl"
        >
          ¿Qué querés revisar hoy?
        </h1>
        <p className="mt-3 max-w-[64ch] text-base leading-relaxed text-text-secondary">
          Elegí primero el tipo de material. Después te mostramos sólo el flujo
          que corresponde, con carga, progreso y resultado contextual.
        </p>

        <div className="mt-6 grid gap-3">
          {OPTIONS.map((option) => (
            <IntentCard key={option.id} option={option} onSelect={onSelect} />
          ))}
        </div>
      </div>

      <aside className="rounded-[var(--radius-panel)] border border-border bg-surface-muted p-5 shadow-[var(--shadow-soft)] lg:sticky lg:top-6">
        <div className="flex items-center gap-3">
          <span className="inline-flex size-10 items-center justify-center rounded-full bg-accent-light text-accent">
            <ShieldCheck size={20} weight="bold" aria-hidden />
          </span>
          <div>
            <p className="text-sm font-semibold text-text-primary">
              Un flujo a la vez
            </p>
            <p className="text-xs text-text-secondary">
              Sin mezclar contrato y valla antes de elegir.
            </p>
          </div>
        </div>
        <div className="mt-5 space-y-3 text-sm leading-relaxed text-text-secondary">
          <p>
            En escritorio, la columna derecha cambia según tu selección: vista
            de contrato para documentos o vista de proyecto para vallas.
          </p>
          <p>
            En móvil, avanzás en una sola columna para mantener la decisión, la
            carga y el resultado claros.
          </p>
        </div>
      </aside>
    </section>
  );
}

function IntentCard({
  option,
  onSelect,
}: {
  option: IntentOption;
  onSelect: (intent: ScanIntent) => void;
}) {
  const Icon = option.icon;
  return (
    <button
      type="button"
      onClick={() => onSelect(option.id)}
      className={cx(
        "group flex min-h-[148px] w-full items-start gap-4 rounded-[var(--radius-card)] border border-border bg-surface p-4 text-left transition-[background-color,border-color,transform] duration-[var(--motion-fast)] hover:border-accent hover:bg-accent-light/60 active:translate-y-px",
        focusRing,
      )}
    >
      <span className="inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-surface-muted text-accent transition-[background-color,color] duration-[var(--motion-fast)] group-hover:bg-accent group-hover:text-white">
        <Icon size={22} weight="regular" aria-hidden />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-lg font-semibold leading-tight text-text-primary">
          {option.title}
        </span>
        <span className="mt-2 block text-sm leading-relaxed text-text-secondary">
          {option.description}
        </span>
        <span className="mt-2 block text-xs leading-relaxed text-text-secondary">
          {option.details}
        </span>
        <span className="mt-3 block text-xs font-medium text-accent">
          {option.action}
        </span>
      </span>
    </button>
  );
}
