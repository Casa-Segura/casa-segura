"use client";

import { Info, Wrench } from "@phosphor-icons/react";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ProjectVerificationFlowShell } from "@/components/project-verification-flow-shell";

export default function ProjectVerificationNotFound() {
  return (
    <ProjectVerificationFlowShell>
      <main
        id="main-content"
        tabIndex={-1}
        className="flex flex-1 flex-col justify-center gap-6 pb-12 outline-none"
      >
        <div className="flex flex-col items-center gap-4 text-center sm:items-start sm:text-start">
          <span
            className="flex size-[5.5rem] items-center justify-center rounded-full bg-surface-muted text-text-secondary ring-2 ring-border"
            aria-hidden
          >
            <Wrench size={40} weight="duotone" />
          </span>
          <div>
            <h1 className="text-balance text-xl font-semibold text-text-primary sm:text-2xl">
              Esta sección no está disponible en esta instalación
            </h1>
            <p className="mt-3 max-w-prose text-base leading-relaxed text-text-secondary">
              La verificación opcional de proyecto o valla no está habilitada en esta
              instancia según configuración actual. Tu flujo principal queda igual: podés
              analizar contratos cuando quieras.
            </p>
          </div>
        </div>

        <aside
          className="rounded-[var(--radius-input)] border border-accent/35 bg-accent-light p-4"
          aria-label="Aclaración"
        >
          <div className="flex gap-3">
            <Info
              size={22}
              className="shrink-0 text-accent pt-0.5"
              weight="bold"
              aria-hidden
            />
            <p className="text-sm leading-relaxed text-text-primary">
              El análisis de contratos sigue disponible; esta beta no bloquea /subir
              ni otras páginas.
            </p>
          </div>
        </aside>

        <div className="flex flex-col gap-3">
          <Link
            href="/subir"
            className="inline-flex min-h-[44px] w-full max-w-sm items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:w-fit"
          >
            Ir a analizar un contrato
          </Link>
          <Link
            href="/"
            className="inline-flex min-h-[44px] max-w-fit items-center text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Volver al inicio
          </Link>
        </div>
      </main>
      <footer className="mt-auto border-t border-border pt-6 pb-2">
        <DisclaimerFooter />
      </footer>
    </ProjectVerificationFlowShell>
  );
}
