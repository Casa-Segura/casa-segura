import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerCallout } from "@/components/disclaimer-callout";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ProjectVerificationFlowShell } from "@/components/project-verification-flow-shell";
import { ProjectVerificationOptionalContractCta } from "@/components/project-verification-optional-contract-cta";
import { ProjectVerificationVerdictIcon } from "@/components/project-verification-verdict-icon";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer-registry";
import { isProjectVerificationDemoLinksEnabled } from "@/lib/project-verification-env";
import { getProjectVerificationFixture } from "@/lib/project-verification-fixtures";
import type { ProjectVerificationVerdict } from "@/lib/project-verification-types";
import { verdictVisualTone } from "@/lib/project-verification-verdict-styles";
import { projectVerificationPreviewFromVerdictFlash } from "@/lib/project-verification-result-map";
import { fetchProjectVerificationDemoResult } from "@/server/project-verification-backend";
import { consumeProjectVerificationVerdictFlashCookie } from "@/server/project-verification-verdict-flash-cookie";

export const metadata: Metadata = {
  title: `Resultado — verificación de proyecto — Casa Segura`,
  description: `Vista opcional tras verificación de proyecto. ${DISCLAIMER_SHORT}.`,
};

type ResultPageProps = {
  searchParams?: Promise<{ v?: string }>;
};

function verdictBandDemoLinks() {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="font-medium text-text-primary">
        Ejemplos de bandas (solo demo):
      </span>
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
  const demosEnabled = isProjectVerificationDemoLinksEnabled();

  const flash = await consumeProjectVerificationVerdictFlashCookie();

  let preview = flash ? projectVerificationPreviewFromVerdictFlash(flash) : null;
  let origin: "flash" | "demo_remote" | "demo_fixture" | "missing" =
    preview ? "flash" : "missing";

  if (!preview && demosEnabled) {
    const remote = await fetchProjectVerificationDemoResult(sp.v);
    preview = remote ?? getProjectVerificationFixture(sp.v);
    origin = remote ? "demo_remote" : "demo_fixture";
  }

  if (!preview) {
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

        <div className="mb-4 max-w-xl">
          <DisclaimerCallout variant="inline" />
        </div>

        <main
          id="main-content"
          tabIndex={-1}
          className="flex flex-1 flex-col gap-6 outline-none"
        >
          <section className="rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
            <h1 className="text-xl font-semibold text-text-primary">
              Todavía no hay un resultado listo para mostrar
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-text-secondary">
              Volvé a completar manual o foto: cuando el servidor procese tus datos vas
              a ver el veredicto acá apenas termines ese paso con la verificación habilitada.
            </p>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/verificacion-proyecto/manual"
                className="inline-flex min-h-[44px] items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-sm font-semibold text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Ir al formulario manual
              </Link>
              <Link
                href="/verificacion-proyecto/foto"
                className="inline-flex min-h-[44px] items-center justify-center rounded-[var(--radius-input)] border border-border bg-surface px-4 py-3 text-sm font-semibold text-accent shadow-sm transition-colors hover:bg-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Volver al paso foto
              </Link>
            </div>
          </section>
        </main>

        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </ProjectVerificationFlowShell>
    );
  }

  const tone = verdictVisualTone(preview.verdict as ProjectVerificationVerdict);
  const isFlash = origin === "flash";
  const showDemoSwitcher =
    demosEnabled && (origin === "demo_remote" || origin === "demo_fixture");

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

      <div className="mb-4 max-w-xl">
        <DisclaimerCallout variant="inline" />
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
                  {isFlash ? "Resultado reciente (local)" : "Ejemplo / demo"}
                </p>
                <h1
                  className={`mt-2 text-balance text-xl font-semibold leading-snug sm:text-[22px] ${tone.title}`}
                >
                  {preview.headline}
                </h1>
                <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                  Esto resume señales técnicas y no reemplaza asesoría legal. Para
                  vallas sí usamos tus campos declarados junto al chequeo de formato;
                  reputación sólo aparece si habilitamos una fuente configurada para
                  este ambiente.
                </p>

                {!isFlash ? (
                  <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                    En modo demo el texto también{" "}
                    <strong className="font-semibold text-text-primary">
                      puede no estar atado al backend real
                    </strong>
                    . Usalo para conocer cómo vas a ver el formato final.
                  </p>
                ) : null}

                {preview.referenceId ? (
                  <p className="mt-3 rounded-[var(--radius-input)] border border-border bg-white/70 px-3 py-2 font-mono text-xs break-words text-text-primary">
                    Referencia de este intento: <span>{preview.referenceId}</span>
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

          {showDemoSwitcher ? (
            <nav
              aria-label="Ejemplos de resultado por banda"
              className="rounded-[var(--radius-input)] border border-border bg-surface px-4 py-3 text-xs lg:hidden"
            >
              <div className="text-text-secondary">{verdictBandDemoLinks()}</div>
            </nav>
          ) : null}
        </div>

        <aside
          className="flex flex-col gap-6 lg:sticky lg:top-6"
          aria-label="Atajos y opciones"
        >
          {showDemoSwitcher ? (
            <nav
              aria-label="Ejemplos de resultado por banda"
              className="rounded-[var(--radius-input)] border border-border bg-surface px-4 py-3 text-xs max-lg:hidden"
            >
              <div className="text-text-secondary">{verdictBandDemoLinks()}</div>
            </nav>
          ) : null}

          <nav
            aria-label="Siguientes pasos opcionales"
            className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-dashed border-border bg-surface p-5 shadow-sm"
          >
            <ProjectVerificationOptionalContractCta />
            <p className="text-center text-sm text-text-secondary">
              Tu contrato existe como flujo diferente desde el menú inicial.
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
