import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";
import { getProjectVerificationFixture } from "@/lib/project-verification-fixtures";
import type { ProjectVerificationVerdict } from "@/lib/project-verification-types";
import { fetchProjectVerificationDemoResult } from "@/server/project-verification-backend";

function verdictBannerClass(verdict: ProjectVerificationVerdict): string {
  switch (verdict) {
    case "green":
      return "border-verdict-green bg-verdict-green-bg text-verdict-green";
    case "red":
      return "border-verdict-red bg-verdict-red-bg text-verdict-red";
    default:
      return "border-verdict-yellow bg-verdict-yellow-bg text-verdict-yellow";
  }
}

export const metadata: Metadata = {
  title: `Resultado (demo) — verificación de proyecto — Casa Segura`,
  description: `Vista de verificación opcional con datos de ejemplo. ${DISCLAIMER_SHORT}.`,
};

type ResultPageProps = {
  searchParams?: Promise<{ v?: string; id?: string }>;
};

export default async function ProjectVerificationResultPage({
  searchParams,
}: ResultPageProps) {
  const sp = (await searchParams) ?? {};
  const remote = await fetchProjectVerificationDemoResult(sp.v);
  const preview = remote ?? getProjectVerificationFixture(sp.v);
  const referenceId = sp.id?.trim() || null;

  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[640px] flex-1 flex-col gap-6">
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
          <header
            className={`rounded-[var(--radius-card)] border-2 p-5 shadow-sm ${verdictBannerClass(preview.verdict)}`}
          >
            <p className="text-xs font-semibold uppercase tracking-wide opacity-90">
              Resultado demo
            </p>
            <h1 className="mt-2 text-balance text-xl font-semibold leading-snug">
              {preview.headline}
            </h1>
            <p className="mt-3 text-sm leading-relaxed opacity-90">
              Esta pantalla muestra la forma del resultado, no una consulta real
              de permisos o reputación. Cuando exista un job de backend, podrá
              abrirse con una referencia o ID de estado.
            </p>
            {referenceId ? (
              <p className="mt-3 rounded-[var(--radius-input)] border border-current/30 px-3 py-2 font-mono text-xs break-words opacity-90">
                ID solicitado: {referenceId}
              </p>
            ) : null}
            {preview.dataFreshnessNote ? (
              <p className="mt-3 text-xs leading-snug opacity-90">
                {preview.dataFreshnessNote}
              </p>
            ) : null}
          </header>

          <section
            aria-labelledby="rationale-heading"
            className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-sm"
          >
            <h2
              id="rationale-heading"
              className="text-base font-semibold text-text-primary"
            >
              Detalle
            </h2>
            <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-text-secondary">
              {preview.rationale.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </section>

          <section
            aria-labelledby="future-state-heading"
            className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-sm"
          >
            <h2
              id="future-state-heading"
              className="text-base font-semibold text-text-primary"
            >
              Cómo se conectará después
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-text-secondary">
              El diseño ya separa la vista demo de un resultado real. Más
              adelante `/resultado?id=...` o una ruta por referencia podrá
              consultar el estado del job sin cambiar el flujo de captura.
            </p>
          </section>

          <nav aria-label="Siguientes pasos" className="flex flex-col gap-3">
            <Link
              href="/subir"
              className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-center text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Analizar un contrato (opcional)
            </Link>
            <p className="text-center text-sm text-text-secondary">
              Podés ignorar esta pantalla; el flujo principal sigue siendo
              independiente.
            </p>
            <div className="flex flex-wrap justify-center gap-2 text-xs text-text-secondary">
              <span>Otras demos:</span>
              <Link
                href="/verificacion-proyecto/resultado?v=green"
                className="font-medium text-accent underline-offset-4 hover:underline"
              >
                verde
              </Link>
              <span aria-hidden>·</span>
              <Link
                href="/verificacion-proyecto/resultado?v=yellow"
                className="font-medium text-accent underline-offset-4 hover:underline"
              >
                amarillo
              </Link>
              <span aria-hidden>·</span>
              <Link
                href="/verificacion-proyecto/resultado?v=red"
                className="font-medium text-accent underline-offset-4 hover:underline"
              >
                rojo
              </Link>
            </div>
          </nav>
        </main>

        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
