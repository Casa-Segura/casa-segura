import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ProjectVerificationFlowShell } from "@/components/project-verification-flow-shell";
import { ProjectVerificationOptionalContractCta } from "@/components/project-verification-optional-contract-cta";
import { ProjectVerificationVerdictIcon } from "@/components/project-verification-verdict-icon";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer-registry";
import { getProjectVerificationFixture } from "@/lib/project-verification-fixtures";
import type { ProjectVerificationVerdict } from "@/lib/project-verification-types";
import { verdictVisualTone } from "@/lib/project-verification-verdict-styles";
import { fetchProjectVerificationDemoResult } from "@/server/project-verification-backend";

export const metadata: Metadata = {
  title: `Resultado (demo) — verificación de proyecto — Casa Segura`,
  description: `Vista de verificación opcional con datos de ejemplo. ${DISCLAIMER_SHORT}.`,
};

type ResultPageProps = {
  searchParams?: Promise<{ v?: string; id?: string }>;
};

function verdictBandSwitchLinks() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="font-medium text-text-primary">Otros demos:</span>
      <Link
        href="/verificacion-proyecto/resultado?v=green"
        className="font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        verde
      </Link>
      <span aria-hidden className="text-text-secondary">
        ·
      </span>
      <Link
        href="/verificacion-proyecto/resultado?v=yellow"
        className="font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        amarillo
      </Link>
      <span aria-hidden className="text-text-secondary">
        ·
      </span>
      <Link
        href="/verificacion-proyecto/resultado?v=red"
        className="font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        rojo
      </Link>
    </div>
  );
}

export default async function ProjectVerificationResultPage({
  searchParams,
}: ResultPageProps) {
  const sp = (await searchParams) ?? {};
  const remote = await fetchProjectVerificationDemoResult(sp.v);
  const preview = remote ?? getProjectVerificationFixture(sp.v);
  const referenceId = sp.id?.trim() || null;
  const tone = verdictVisualTone(preview.verdict as ProjectVerificationVerdict);

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
        className="flex flex-1 flex-col gap-6 outline-none lg:grid lg:grid-cols-[minmax(0,3fr)_minmax(260px,1fr)] lg:items-start lg:gap-x-10"
      >
        <div className="flex flex-col gap-6">
          <header
            className={`rounded-[var(--radius-card)] p-5 shadow-sm ${tone.container}`}
          >
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
              <div
                className={`flex shrink-0 items-center justify-center rounded-[var(--radius-hero)] p-3 shadow-sm ${tone.iconRing}`}
              >
                <ProjectVerificationVerdictIcon verdict={preview.verdict} />
              </div>
              <div className="min-w-0 flex-1">
                <p
                  className={`text-xs font-semibold uppercase tracking-wide ${tone.title}`}
                >
                  Resultado demo
                </p>
                <h1
                  className={`mt-2 text-balance text-xl font-semibold leading-snug sm:text-[22px] ${tone.title}`}
                >
                  {preview.headline}
                </h1>
                <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                  Esta pantalla solo muestra el formato esperado cuando exista
                  backend; en demo, el texto de la valla{" "}
                  <strong className="font-semibold text-text-primary">
                    no se cruza con registros externos
                  </strong>
                  . Cuando el job esté listo, vas a abrir el estado real desde una
                  referencia o ID sin cambiar cómo cargás los datos.
                </p>
                {referenceId ? (
                  <p className="mt-3 rounded-[var(--radius-input)] border border-border bg-white/70 px-3 py-2 font-mono text-xs break-words text-text-primary">
                    Referencia solicitada: <span>{referenceId}</span>
                  </p>
                ) : null}
                {preview.dataFreshnessNote ? (
                  <p className="mt-3 text-xs leading-snug text-text-secondary">
                    {preview.dataFreshnessNote}
                  </p>
                ) : null}
              </div>
            </div>
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
              El diseño ya separa la vista demo de un resultado real. Más adelante
              `/resultado?id=...` u otra ruta por referencia podrá consultar el
              estado del job sin cambiar el flujo de captura.
            </p>
          </section>

          <nav
            aria-label="Ejemplos de resultado por banda"
            className="rounded-[var(--radius-input)] border border-border bg-surface px-4 py-3 text-xs lg:hidden"
          >
            <div className="text-text-secondary">{verdictBandSwitchLinks()}</div>
          </nav>
        </div>

        <aside
          className="flex flex-col gap-6 lg:sticky lg:top-6"
          aria-label="Atajos y opciones"
        >
          <nav
            aria-label="Ejemplos de resultado por banda"
            className="rounded-[var(--radius-input)] border border-border bg-surface px-4 py-3 text-xs max-lg:hidden"
          >
            <div className="text-text-secondary">{verdictBandSwitchLinks()}</div>
          </nav>

          <nav
            aria-label="Siguientes pasos opcionales"
            className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-dashed border-border bg-surface p-5 shadow-sm"
          >
            <ProjectVerificationOptionalContractCta />
            <p className="text-center text-sm text-text-secondary">
              Podés ignorar estas sugerencias: el contrato ya es accesible desde el
              inicio y desde el pie de página.
            </p>
          </nav>
        </aside>
      </main>

      <footer className="mt-auto border-t border-border pt-6 pb-2">
        <DisclaimerFooter />
      </footer>
    </ProjectVerificationFlowShell>
  );
}
