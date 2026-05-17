"use client";

import { ArrowCounterClockwise, Camera, CheckCircle } from "@phosphor-icons/react";
import { useState } from "react";
import {
  CasaButton,
  DisclaimerPanel,
  ProgressTimeline,
  SkeletonBlock,
  StatusPill,
  cx,
  scanFlowDesktopSplitGridClass,
  type ProgressStep,
} from "@/components/casa-ui";
import { ContractUploadFlow } from "@/components/contract-upload-flow";
import {
  ProjectVerificationBillboardUploadForm,
  type BillboardDesktopCompanionPhase,
} from "@/components/project-verification-billboard-upload-form";
import {
  ScanIntentSelector,
  type ScanIntent,
} from "@/components/scan-intent-selector";

const billboardSteps: ProgressStep[] = [
  {
    id: "photo",
    label: "Foto recibida",
    detail: "Usamos la imagen sólo para este intento.",
    state: "active",
  },
  {
    id: "ocr",
    label: "Detectando datos visibles",
    detail: "Nombre del proyecto, desarrollador, permiso y dirección.",
    state: "pending",
  },
  {
    id: "verify",
    label: "Preparando verificación",
    detail: "La lectura automática se conectará al backend de verificación.",
    state: "pending",
  },
];

const billboardStepsLoading: ProgressStep[] = billboardSteps.map((step, i) => ({
  ...step,
  state: i === 0 ? "done" : i === 1 ? "active" : "pending",
}));

const billboardStepsComplete: ProgressStep[] = billboardSteps.map((step) => ({
  ...step,
  state: "done",
}));

export function ScanFlowShell() {
  const [intent, setIntent] = useState<ScanIntent | null>(null);

  if (!intent) {
    return <ScanIntentSelector onSelect={setIntent} />;
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-col gap-3 rounded-[var(--radius-panel)] border border-border bg-surface p-4 shadow-[var(--shadow-soft)] sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
            Tipo de revisión
          </p>
          <p className="mt-1 text-base font-semibold text-text-primary">
            {intent === "contract"
              ? "Contrato de compra o alquiler"
              : "Valla publicitaria / proyecto"}
          </p>
        </div>
        <CasaButton
          variant="secondary"
          onClick={() => setIntent(null)}
          className="w-full text-sm sm:w-auto"
        >
          <ArrowCounterClockwise size={16} aria-hidden />
          Cambiar tipo
        </CasaButton>
      </div>

      {intent === "contract" ? <ContractUploadFlow /> : <BillboardBranch />}
    </div>
  );
}

function BillboardBranch() {
  const [companionPhase, setCompanionPhase] =
    useState<BillboardDesktopCompanionPhase>("idle");

  return (
    <div className={scanFlowDesktopSplitGridClass}>
      <section className="flex flex-col gap-6 self-start rounded-[var(--radius-panel)] border border-border bg-surface p-5 shadow-[var(--shadow-soft)] sm:p-6">
        <header>
          <StatusPill tone="accent">Paso 2 de 4 · Subir valla</StatusPill>
          <h1 className="mt-4 text-balance text-2xl font-semibold tracking-tight text-text-primary">
            Subí una foto clara de la valla
          </h1>
          <p className="mt-2 text-base leading-relaxed text-text-secondary">
            Capturá el letrero, anuncio o valla del proyecto. Buscamos señales
            visibles como nombre, desarrollador, permiso y dirección.
          </p>
        </header>

        <ProjectVerificationBillboardUploadForm
          onCompanionPhaseChange={setCompanionPhase}
        />

        <DisclaimerPanel tone="neutral">
          <p className="font-medium text-text-primary">
            Esto no reemplaza verificación legal o registral.
          </p>
          <p className="mt-1 text-text-secondary">
            La foto ayuda a orientar la revisión del proyecto y puede continuar
            con un análisis de contrato cuando tengas el documento.
          </p>
        </DisclaimerPanel>
      </section>

      <BillboardWorkbench phase={companionPhase} />
    </div>
  );
}

function BillboardWorkbench({ phase }: { phase: BillboardDesktopCompanionPhase }) {
  const idle = phase === "idle";
  const loading = phase === "loading";

  return (
    <section
      className={cx(
        "hidden overflow-hidden rounded-[var(--radius-panel)] border border-border bg-surface-muted shadow-[var(--shadow-panel)] lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]",
        idle ? "min-h-[520px]" : "min-h-[760px]",
      )}
      aria-label="Mesa de verificación de valla"
    >
      <div className="flex min-h-0 min-w-0 flex-col border-r border-border bg-surface">
        <header className="flex min-h-[52px] items-center justify-between border-b border-border px-5">
          <div className="flex min-w-0 items-center gap-2 text-sm font-semibold text-text-primary">
            <Camera size={18} className="shrink-0 text-accent" aria-hidden />
            <span className="truncate">Valla publicitaria</span>
          </div>
          {idle ? (
            <StatusPill tone="accent">Vista previa</StatusPill>
          ) : loading ? (
            <StatusPill tone="yellow" pulse>
              Leyendo foto
            </StatusPill>
          ) : (
            <StatusPill tone="green">Foto recibida</StatusPill>
          )}
        </header>
        <div className="flex flex-1 items-center justify-center bg-[#111111] p-6">
          <BillboardPhotoFrame phase={phase} />
        </div>
      </div>

      <aside className="flex min-h-0 min-w-0 flex-col bg-surface-muted">
        <header className="border-b border-border bg-surface px-5 py-3">
          <span className="text-xs font-medium text-text-secondary">
            {idle
              ? "Sin envío aún"
              : loading
                ? "Procesando imagen…"
                : "Seguí en el formulario o en verificación manual"}
          </span>
        </header>
        <div className="min-h-0 flex-1 overflow-y-auto p-5">
          {idle ? (
            <BillboardCompanionIdle />
          ) : loading ? (
            <div className="flex flex-col gap-5">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
                  En vivo
                </p>
                <h2 className="mt-2 text-xl font-semibold tracking-tight text-text-primary">
                  Extrayendo señales de la foto
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                  Enviamos la imagen y preparamos la lectura de proyecto,
                  desarrollador y datos visibles en la valla.
                </p>
              </div>
              <ProgressTimeline steps={billboardStepsLoading} progress={48} />
              <section
                className="rounded-[var(--radius-card)] border border-border bg-surface p-4"
                aria-label="Leyendo campos visibles"
              >
                <div className="mb-3 flex items-center justify-between gap-3">
                  <SkeletonBlock className="h-3 w-28" label="Leyendo texto visible" />
                  <SkeletonBlock className="h-3 w-14" label="Progreso parcial" />
                </div>
                <div className="flex flex-col gap-2">
                  <SkeletonBlock className="h-12 w-full" label="Dato detectado" />
                  <SkeletonBlock className="h-12 w-full" label="Dato detectado" />
                  <SkeletonBlock className="h-12 w-10/12" label="Dato detectado" />
                </div>
              </section>
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              <div className="flex items-start gap-3 rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-[var(--shadow-soft)]">
                <span className="inline-flex size-11 shrink-0 items-center justify-center rounded-full bg-verdict-green-bg text-verdict-green">
                  <CheckCircle size={22} weight="fill" aria-hidden />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-verdict-green">
                    Recibido
                  </p>
                  <h2 className="mt-1 text-lg font-semibold text-text-primary">
                    La foto llegó al servidor
                  </h2>
                  <p className="mt-2 text-sm leading-relaxed text-text-secondary">
                    Si la lectura automática no alcanza, usá la verificación
                    manual desde el mensaje de confirmación en el formulario.
                  </p>
                </div>
              </div>
              <ProgressTimeline steps={billboardStepsComplete} progress={100} />
            </div>
          )}
        </div>
      </aside>
    </section>
  );
}

function BillboardCompanionIdle() {
  const bullets = [
    "Vista amplia de la valla después del envío.",
    "Pasos de lectura alineados al flujo real.",
    "Espacio para pasar a corrección manual si hace falta.",
  ];

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
          Antes de enviar
        </p>
        <h2 className="mt-2 text-xl font-semibold tracking-tight text-text-primary">
          Mesa de trabajo para la valla
        </h2>
        <p className="mt-2 text-sm leading-relaxed text-text-secondary">
          Esta columna muestra progreso animado sólo mientras se envía y procesa
          la foto. Ahora es una vista previa vacía: no hay datos de tu imagen
          todavía.
        </p>
      </div>
      <section className="rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-[var(--shadow-soft)]">
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

function BillboardPhotoFrame({
  phase,
}: {
  phase: BillboardDesktopCompanionPhase;
}) {
  const idle = phase === "idle";
  const loading = phase === "loading";

  if (idle) {
    return (
      <div className="w-full max-w-[560px] rounded-[var(--radius-panel)] border border-dashed border-white/25 bg-[#1A1A1A]/80 p-6 text-center shadow-[var(--shadow-panel)]">
        <span className="inline-flex size-14 items-center justify-center rounded-full bg-white/10 text-white">
          <Camera size={28} aria-hidden />
        </span>
        <p className="mt-5 text-sm font-semibold text-white">
          Tu foto aparecerá aquí
        </p>
        <p className="mt-2 text-sm leading-relaxed text-white/65">
          Después del envío verás la vista amplia y el estado de lectura; ahora
          no hay imagen en proceso.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="w-full max-w-[560px] overflow-hidden rounded-[var(--radius-panel)] border border-white/10 bg-[#1A1A1A] p-4 shadow-[var(--shadow-panel)]">
        <div className="relative aspect-[4/3] overflow-hidden rounded-[var(--radius-card)] bg-[#252525]">
          <div className="absolute inset-0 bg-gradient-to-br from-[#374151]/90 via-[#1A1A1A] to-[#0F766E]/50 motion-safe:animate-pulse motion-reduce:animate-none" />
          <div className="relative flex h-full flex-col justify-between p-5">
            <div className="space-y-3">
              <SkeletonBlock
                className="h-3 w-24 bg-white/20 before:via-white/35"
                label="Leyendo proyecto"
              />
              <SkeletonBlock
                className="h-7 max-w-[220px] bg-white/15 before:via-white/30"
                label="Leyendo nombre visible"
              />
              <SkeletonBlock
                className="h-3 max-w-[180px] bg-white/15 before:via-white/30"
                label="Leyendo detalle"
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <SkeletonBlock
                className="h-3 w-full bg-white/15 before:via-white/30"
                label="Campo permiso"
              />
              <SkeletonBlock
                className="h-3 w-full bg-white/15 before:via-white/30"
                label="Campo zona"
              />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[560px] overflow-hidden rounded-[var(--radius-panel)] border border-white/10 bg-[#1A1A1A] p-4 shadow-[var(--shadow-panel)]">
      <div className="aspect-[4/3] rounded-[var(--radius-card)] bg-gradient-to-br from-[#374151] via-[#1A1A1A] to-[#0F766E] p-5">
        <div className="flex h-full flex-col justify-between rounded-[var(--radius-card)] border border-white/20 bg-white/10 p-5 text-white backdrop-blur-[2px]">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-white/60">
              Ejemplo visual
            </p>
            <p className="mt-2 text-3xl font-semibold tracking-tight">
              Residencial Las Brisas
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs text-white/75">
            <span>Ilustración posterior al envío exitoso</span>
            <span>Zona: San Salvador</span>
          </div>
        </div>
      </div>
    </div>
  );
}
