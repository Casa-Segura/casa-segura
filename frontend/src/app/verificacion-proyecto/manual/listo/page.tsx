import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ManualVerificationSuccessBadge } from "@/components/manual-verification-success-badge";
import { ProjectVerificationFlowShell } from "@/components/project-verification-flow-shell";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";

export const metadata: Metadata = {
  title: `Datos recibidos — verificación de proyecto — Casa Segura`,
  description: `Confirmación del formulario manual opcional. ${DISCLAIMER_SHORT}.`,
};

type ManualDonePageProps = {
  searchParams?: Promise<{ ref?: string }>;
};

export default async function ProjectVerificationManualDonePage({
  searchParams,
}: ManualDonePageProps) {
  const sp = (await searchParams) ?? {};
  const referenceId = sp.ref?.trim() || null;

  return (
    <ProjectVerificationFlowShell maxWidth="2xl">
      <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-4">
        <Link
          href="/verificacion-proyecto"
          className="inline-flex min-h-[44px] max-w-fit items-center text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Volver a verificación
        </Link>
        <Link
          href="/"
          className="inline-flex min-h-[44px] max-w-fit items-center text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Inicio
        </Link>
      </div>

      <main
        id="main-content"
        tabIndex={-1}
        className="flex flex-1 flex-col gap-6 outline-none lg:grid lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start lg:gap-x-10"
      >
        <div className="flex flex-col gap-6">
          <header className="rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
              <ManualVerificationSuccessBadge />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-accent">
                  Verificación opcional
                </p>
                <h1 className="mt-2 max-w-xl text-balance text-2xl font-semibold leading-tight tracking-tight text-text-primary">
                  Datos del proyecto recibidos
                </h1>
                <p className="mt-3 max-w-xl text-base leading-relaxed text-text-secondary">
                  Guardá esta referencia cuando coordinés con tu equipo o soporte técnico
                  sobre este envío. El análisis de contratos sigue siendo un flujo aparte.
                </p>
                {referenceId ? (
                  <p className="mt-4 rounded-[var(--radius-input)] border border-border bg-accent-light/50 p-3 font-mono text-sm text-text-primary break-words">
                    {referenceId}
                  </p>
                ) : null}
              </div>
            </div>
          </header>

          <section
            aria-labelledby="next-heading"
            className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-sm"
          >
            <h2
              id="next-heading"
              className="text-base font-semibold text-text-primary"
            >
              Qué esperar
            </h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-text-secondary">
              <li>
                Esta versión valida y entrega una referencia; todavía no cruza
                registros reales de permisos o reputación.
              </li>
              <li>
                Cuando exista resultado real por ID, esta referencia podrá abrir
                una pantalla de estado en lugar de la demo.
              </li>
            </ul>
          </section>
        </div>

        <aside
          className="flex flex-col gap-3 lg:sticky lg:top-6"
          aria-label="Siguientes pasos"
        >
          <nav className="flex flex-col gap-3" aria-labelledby="manual-done-nav-h">
            <p id="manual-done-nav-h" className="sr-only">
              Acciones rápidas
            </p>
            <Link
              href="/verificacion-proyecto/resultado"
              className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-center text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Ver resultado demo
            </Link>
            <Link
              href="/subir"
              className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] border border-border bg-surface px-4 py-3 text-center text-base font-semibold text-accent shadow-sm transition-colors hover:bg-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Analizar un contrato (opcional)
            </Link>
          </nav>
        </aside>
      </main>

      <footer className="mt-auto border-t border-border pt-6 pb-2">
        <DisclaimerFooter />
      </footer>
    </ProjectVerificationFlowShell>
  );
}
