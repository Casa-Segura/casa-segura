import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { PUBLIC_SOURCE_REPO_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Casa Segura — Analiza tu contrato antes de firmar",
  description:
    "Herramienta abierta para revisar contratos inmobiliarios con contexto antes de firmar. Esto no es asesoría legal.",
};

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-[var(--spacing-section)] outline-none"
      >
        <header className="shrink-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">
            <span translate="no">Casa Segura</span>
          </p>
        </header>

        <section className="flex flex-1 flex-col gap-5" aria-labelledby="landing-heading">
          <h1
            id="landing-heading"
            className="text-balance text-[1.625rem] font-semibold leading-snug tracking-tight text-text-primary sm:text-3xl"
          >
            Entendé mejor tu contrato de vivienda antes de firmar
          </h1>
          <p className="text-base leading-relaxed text-text-secondary">
            Subí el PDF o fotos del contrato y recibí un informe claro sobre cláusulas repetidas, avisos y riesgos
            típicos. Vos decidís con más contexto; la herramienta es de código abierto y está pensada para El Salvador.
          </p>

          <div className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-sm">
            <h2 className="text-base font-semibold text-text-primary">Empezá ahora</h2>
            <p className="mt-2 text-sm leading-relaxed text-text-secondary">
              El análisis de contratos está disponible en la web. La verificación de proyectos o vallas es una línea de
              trabajo futura; no es necesaria para usar el flujo actual.
            </p>
            <div className="mt-4 flex flex-col gap-3">
              <Link
                href="/subir"
                className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-center text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 active:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
              >
                Analizar un contrato
              </Link>
              <p className="text-center text-sm text-text-secondary">
                En menos de dos minutos. Funciona en el móvil.
              </p>
            </div>
          </div>

          <section className="space-y-4 text-sm leading-relaxed text-text-secondary" aria-labelledby="how-heading">
            <h2 id="how-heading" className="text-base font-semibold text-text-primary">
              Cómo funciona
            </h2>
            <p>
              Extraemos el texto del documento, lo evaluamos con una rúbrica transparente y armamos un informe con
              citas al contrato para que puedas contrastar cada punto.
            </p>
            <p>
              <strong className="font-semibold text-text-primary">Código abierto.</strong> El repositorio público permite
              auditar qué hace la herramienta; la confianza viene de la verificabilidad, no del operador.
            </p>
          </section>
        </section>

        <footer className="mt-auto shrink-0 space-y-6 border-t border-border pt-6 pb-2 text-center">
          <nav aria-label="Enlaces del sitio" className="flex flex-col items-center gap-4 text-sm">
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
              Contacto para verificación de negocio o datos: abrí un issue en el repositorio o escribí al equipo que
              opera tu instancia desplegada.
            </p>
          </nav>
          <DisclaimerFooter />
        </footer>
      </main>
    </div>
  );
}
