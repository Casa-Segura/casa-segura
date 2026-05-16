import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
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
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[560px] flex-1 flex-col gap-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-4">
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
          className="flex flex-1 flex-col gap-6 outline-none"
        >
          <header className="rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-accent">
              Verificación opcional
            </p>
            <h1 className="mt-2 text-balance text-2xl font-semibold leading-tight tracking-tight text-text-primary">
              Datos del proyecto recibidos
            </h1>
            <p className="mt-3 text-base leading-relaxed text-text-secondary">
              Guardá esta referencia para hablar con el equipo que opere tu
              instancia. El análisis de contratos sigue siendo un flujo aparte.
            </p>
            {referenceId ? (
              <p className="mt-4 rounded-[var(--radius-input)] border border-border bg-accent-light/50 p-3 font-mono text-sm text-text-primary break-words">
                {referenceId}
              </p>
            ) : null}
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

          <nav aria-label="Siguientes pasos" className="flex flex-col gap-3">
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
        </main>

        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
