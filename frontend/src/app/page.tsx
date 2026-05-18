import type { Metadata } from "next";
import Link from "next/link";
import { ArrowCta, BrandMark, DocumentPreview } from "@/components/casa-ui";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { TestDataDriveCallout } from "@/components/test-data-drive-callout";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";
import { PUBLIC_SOURCE_REPO_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Casa Segura — Analiza tu contrato antes de firmar",
  description: `Herramienta abierta para revisar contratos inmobiliarios con contexto antes de firmar. ${DISCLAIMER_SHORT}.`,
};

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6 lg:px-8">
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-[var(--spacing-section)] outline-none"
      >
        <header className="flex shrink-0 items-center justify-between">
          <BrandMark />
          <Link
            href="/privacy"
            className="hidden min-h-[44px] items-center rounded-[var(--radius-input)] px-3 text-sm font-medium text-text-secondary underline-offset-4 hover:text-accent hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent sm:inline-flex"
          >
            Privacidad
          </Link>
        </header>

        <section
          className="grid flex-1 gap-8 lg:grid-cols-[minmax(0,0.9fr)_minmax(440px,1.1fr)] lg:items-center lg:gap-12"
          aria-labelledby="landing-heading"
        >
          <div className="flex max-w-[680px] flex-col gap-6">
            <p className="inline-flex w-fit rounded-[var(--radius-pill)] border border-accent/20 bg-accent-light px-3 py-1.5 text-xs font-semibold text-accent">
              Análisis legal asistido para contratos inmobiliarios
            </p>
            <h1
              id="landing-heading"
              className="text-balance text-4xl font-semibold leading-[0.98] tracking-[-0.05em] text-text-primary sm:text-5xl lg:text-6xl"
            >
              Entendé lo que firmas antes de comprometerte.
            </h1>
            <p className="max-w-[60ch] text-base leading-relaxed text-text-secondary sm:text-lg">
              Subí tu contrato inmobiliario y recibí un análisis claro de
              cláusulas repetidas, avisos y riesgos típicos. Vos decidís con más
              contexto; la herramienta está pensada para El Salvador.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link
                href="/subir"
                className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-[var(--radius-input)] bg-accent px-5 py-3 text-center text-base font-semibold text-white shadow-sm transition-[background-color,transform] duration-[var(--motion-fast)] hover:bg-accent/95 active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Analizar un contrato
                <ArrowCta />
              </Link>
            </div>
            <div className="grid grid-cols-3 gap-3 border-t border-border pt-5 text-sm text-text-secondary">
              <div>
                <p className="font-mono text-lg font-semibold text-text-primary">
                  38
                </p>
                <p>criterios legales</p>
              </div>
              <div>
                <p className="font-mono text-lg font-semibold text-text-primary">
                  3
                </p>
                <p>canales de entrega</p>
              </div>
              <div>
                <p className="font-mono text-lg font-semibold text-text-primary">
                  30
                </p>
                <p>días de enlace</p>
              </div>
            </div>
          </div>

          <div className="hidden lg:block">
            <DocumentPreview phase="result" className="mx-auto max-w-[620px]" />
          </div>
        </section>

        <section
          className="grid gap-4 rounded-[var(--radius-panel)] border border-border bg-surface p-5 shadow-[var(--shadow-soft)] lg:grid-cols-[0.8fr_1fr]"
          aria-labelledby="how-heading"
        >
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">
              Cómo funciona
            </p>
            <h2
              id="how-heading"
              className="mt-2 text-balance text-2xl font-semibold tracking-tight text-text-primary"
            >
              Del documento al reporte sin perderte en jerga.
            </h2>
          </div>
          <div className="grid gap-3 text-sm leading-relaxed text-text-secondary sm:grid-cols-3">
            <div className="rounded-[var(--radius-card)] bg-surface-muted p-4">
              <p className="font-semibold text-text-primary">1. Subí</p>
              <p className="mt-2">PDF o fotos nítidas del contrato.</p>
            </div>
            <div className="rounded-[var(--radius-card)] bg-surface-muted p-4">
              <p className="font-semibold text-text-primary">2. Analizamos</p>
              <p className="mt-2">OCR, criterios legales y áreas de interés.</p>
            </div>
            <div className="rounded-[var(--radius-card)] bg-surface-muted p-4">
              <p className="font-semibold text-text-primary">3. Revisás</p>
              <p className="mt-2">Reporte, citas y próximos pasos claros.</p>
            </div>
          </div>
        </section>

        <TestDataDriveCallout />

        <section className="rounded-[var(--radius-panel)] bg-accent p-6 text-white lg:p-10">
          <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-center">
            <div>
              <h2 className="text-balance text-3xl font-semibold tracking-tight">
                Empezá gratis. Comparte con quien lo necesite.
              </h2>
              <p className="mt-3 max-w-[64ch] text-sm leading-relaxed text-white/75">
                El análisis básico no requiere registro ni tarjeta: subí el
                contrato en{" "}
                <Link
                  href="/subir"
                  className="font-semibold text-white underline underline-offset-4 hover:text-white/95 focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
                >
                  /subir
                </Link>{" "}
                y seguí el informe paso a paso.
              </p>
            </div>
            <Link
              href="/subir"
              className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-[var(--radius-input)] bg-white px-5 py-3 text-base font-semibold text-accent transition-[transform,opacity] duration-[var(--motion-fast)] hover:opacity-95 active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Subir contrato
              <ArrowCta />
            </Link>
          </div>
        </section>

        <section
          className="mx-auto max-w-[760px] space-y-4 text-center text-sm leading-relaxed text-text-secondary"
          aria-labelledby="trust-heading"
        >
          <h2
            id="trust-heading"
            className="text-balance text-2xl font-semibold tracking-tight text-text-primary"
          >
            No somos abogados. Te hacemos llegar preparado.
          </h2>
          <p>
            Extraemos texto, evaluamos una rúbrica transparente y armamos un
            informe con citas al contrato para que puedas contrastar cada punto.
          </p>
          <p>
            <strong className="font-semibold text-text-primary">
              Código abierto.
            </strong>{" "}
            El repositorio público permite auditar qué hace la herramienta; la
            confianza viene de la verificabilidad, no del operador.
          </p>
        </section>

        <footer className="mt-auto shrink-0 space-y-6 border-t border-border pt-6 pb-2 text-center">
          <nav
            aria-label="Enlaces del sitio"
            className="flex flex-col items-center gap-4 text-sm"
          >
            <div className="flex flex-col items-center gap-2 sm:flex-row sm:flex-wrap sm:justify-center sm:gap-x-6 sm:gap-y-2">
              <Link
                href="/privacy"
                className="inline-flex min-h-[44px] max-w-fit items-center justify-center font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Política de privacidad
              </Link>
              <a
                href={PUBLIC_SOURCE_REPO_URL}
                rel="noopener noreferrer"
                className="inline-flex min-h-[44px] max-w-fit items-center justify-center font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Código fuente en GitHub
              </a>
            </div>
            <p className="mx-auto max-w-prose text-xs leading-snug text-text-secondary">
              Contacto para verificación de negocio o datos: abrí un issue en el
              repositorio o escribí al equipo que opera tu instancia desplegada.
            </p>
          </nav>
          <DisclaimerFooter />
        </footer>
      </main>
    </div>
  );
}
