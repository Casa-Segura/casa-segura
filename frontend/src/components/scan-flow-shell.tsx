"use client";

import { ArrowCounterClockwise, Camera, CheckCircle } from "@phosphor-icons/react";
import { useState } from "react";
import {
  CasaButton,
  DisclaimerPanel,
  ProgressTimeline,
  StatusPill,
  type ProgressStep,
} from "@/components/casa-ui";
import { ContractUploadFlow } from "@/components/contract-upload-flow";
import { ProjectVerificationBillboardUploadForm } from "@/components/project-verification-billboard-upload-form";
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
  return (
    <div className="grid w-full gap-6 lg:grid-cols-[minmax(360px,440px)_1fr] lg:items-start">
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

        <ProjectVerificationBillboardUploadForm />

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

      <BillboardPreviewPanel />
    </div>
  );
}

function BillboardPreviewPanel() {
  return (
    <section
      className="hidden min-h-[760px] overflow-hidden rounded-[var(--radius-panel)] border border-border bg-surface-muted shadow-[var(--shadow-panel)] lg:flex lg:flex-col"
      aria-label="Vista de verificación de valla"
    >
      <header className="flex min-h-[52px] items-center justify-between border-b border-border bg-surface px-5">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <Camera size={18} className="text-accent" aria-hidden />
          Valla publicitaria
        </div>
        <StatusPill tone="accent">Vista previa</StatusPill>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_360px]">
        <div className="flex items-center justify-center border-r border-border bg-[#111111] p-6">
          <div className="w-full max-w-[560px] overflow-hidden rounded-[var(--radius-panel)] border border-white/10 bg-[#1A1A1A] p-4 shadow-[var(--shadow-panel)]">
            <div className="aspect-[4/3] rounded-[var(--radius-card)] bg-gradient-to-br from-[#374151] via-[#1A1A1A] to-[#0F766E] p-5">
              <div className="flex h-full flex-col justify-between rounded-[var(--radius-card)] border border-white/20 bg-white/10 p-5 text-white backdrop-blur-[2px]">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-white/60">
                    Proyecto
                  </p>
                  <p className="mt-2 text-3xl font-semibold tracking-tight">
                    Residencial Las Brisas
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs text-white/75">
                  <span>Permiso: pendiente de lectura</span>
                  <span>Zona: San Salvador</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <aside className="flex min-w-0 flex-col bg-surface-muted">
          <div className="border-b border-border bg-surface p-5">
            <div className="flex items-center gap-3">
              <span className="inline-flex size-12 items-center justify-center rounded-full bg-accent-light text-accent">
                <CheckCircle size={24} weight="fill" aria-hidden />
              </span>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
                  Próximo paso
                </p>
                <h2 className="text-lg font-semibold text-text-primary">
                  Detectar datos visibles
                </h2>
              </div>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">
              La verificación de valla prepara el terreno antes de subir el
              contrato. Si algo no se lee, podrás corregirlo manualmente.
            </p>
          </div>

          <div className="min-h-0 flex-1 overflow-y-auto p-5">
            <ProgressTimeline steps={billboardSteps} progress={22} />
          </div>
        </aside>
      </div>
    </section>
  );
}
