import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";

export const metadata: Metadata = {
  title: `Verificación de proyecto (opcional) — Casa Segura`,
  description: `Flujo opcional, independiente del análisis de contratos. ${DISCLAIMER_SHORT}.`,
};

export default function ProjectVerificationHubPage() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col overflow-x-hidden bg-bg px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-8">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <Link
            href="/"
            className="inline-flex min-h-[44px] max-w-fit items-center text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Volver al inicio
          </Link>
          <Link
            href="/subir"
            className="inline-flex min-h-[44px] max-w-fit items-center justify-center rounded-[var(--radius-input)] border border-border bg-surface px-4 py-2 text-sm font-semibold text-accent shadow-sm transition-colors hover:bg-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Analizar contrato
          </Link>
        </header>

        <main
          id="main-content"
          tabIndex={-1}
          className="flex flex-1 flex-col gap-10 outline-none"
        >
          <section className="grid gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)] lg:items-center">
            <div className="flex flex-col gap-6">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-accent">
                  <span translate="no">Casa Segura</span> beta opcional
                </p>
                <h1 className="mt-3 max-w-[12ch] text-balance text-4xl font-semibold leading-[0.98] tracking-tight text-text-primary sm:text-5xl lg:text-6xl">
                  Verificá señales antes de apartar una vivienda
                </h1>
                <p className="mt-5 max-w-[62ch] text-base leading-relaxed text-text-secondary sm:text-lg">
                  Tomá una foto de la valla del proyecto o completá los datos a
                  mano. Esta verificación no bloquea el análisis de contratos:
                  suma contexto temprano cuando todavía estás comparando
                  opciones.
                </p>
              </div>

              <nav
                aria-label="Elegí cómo iniciar la verificación"
                className="grid gap-3 sm:grid-cols-2"
              >
                <Link
                  href="/verificacion-proyecto/foto"
                  className="flex min-h-[56px] items-center justify-center rounded-[var(--radius-input)] bg-accent px-5 py-4 text-center text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 active:translate-y-px focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                >
                  Sacar o subir foto
                </Link>
                <Link
                  href="/verificacion-proyecto/manual"
                  className="flex min-h-[56px] items-center justify-center rounded-[var(--radius-input)] border border-border bg-surface px-5 py-4 text-center text-base font-semibold text-accent shadow-sm transition-colors hover:bg-accent-light focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                >
                  Completar a mano
                </Link>
              </nav>
            </div>

            <aside
              aria-label="Vista previa del flujo de verificación"
              className="rounded-[2rem] border border-border bg-surface p-4 shadow-[0_20px_40px_-24px_rgba(31,26,20,0.35)]"
            >
              <div className="rounded-[1.5rem] border border-border bg-bg p-4">
                <div className="aspect-[4/3] rounded-[1.25rem] border border-border bg-surface p-4">
                  <div className="flex h-full flex-col justify-between rounded-[1rem] bg-accent-light p-4">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-accent">
                        Valla detectada
                      </p>
                      <div className="mt-4 h-3 w-3/4 rounded-full bg-accent/70" />
                      <div className="mt-3 h-3 w-1/2 rounded-full bg-accent/40" />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <span className="h-16 rounded-[var(--radius-input)] bg-surface/90" />
                      <span className="h-16 rounded-[var(--radius-input)] bg-surface/70" />
                    </div>
                  </div>
                </div>
                <div className="mt-4 grid gap-3 text-sm">
                  <div className="rounded-[var(--radius-input)] border border-border bg-surface p-3">
                    <p className="font-semibold text-text-primary">
                      1. Foto de la valla
                    </p>
                    <p className="mt-1 text-text-secondary">
                      El stub confirma recepción sin guardar imagen.
                    </p>
                  </div>
                  <div className="rounded-[var(--radius-input)] border border-border bg-surface p-3">
                    <p className="font-semibold text-text-primary">
                      2. Corrección manual
                    </p>
                    <p className="mt-1 text-text-secondary">
                      Si el OCR falla, revisás campos antes de enviar.
                    </p>
                  </div>
                </div>
              </div>
            </aside>
          </section>

          <section
            aria-labelledby="project-verification-details"
            className="grid gap-4 md:grid-cols-[1.1fr_0.9fr]"
          >
            <div className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-sm">
              <h2
                id="project-verification-details"
                className="text-lg font-semibold text-text-primary"
              >
                Qué hace esta beta
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                Ordena datos visibles de la valla: desarrollador, nombre del
                proyecto, permiso y dirección aproximada. Más adelante el
                backend podrá consultar registros reales y devolver un estado
                por ID.
              </p>
            </div>
            <div
              aria-labelledby="project-verification-notice"
              className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-sm"
            >
              <h2
                id="project-verification-notice"
                className="text-lg font-semibold text-text-primary"
              >
                Independiente del contrato
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-text-secondary">
                Podés saltarte este paso. El informe de contratos vive en{" "}
                <Link
                  href="/subir"
                  className="font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
                >
                  /subir
                </Link>{" "}
                y no necesita una verificación previa del proyecto.
              </p>
            </div>
          </section>

          <Link
            href="/verificacion-proyecto/resultado"
            className="inline-flex min-h-[44px] max-w-fit items-center justify-center rounded-[var(--radius-input)] border border-dashed border-border bg-surface px-4 py-3 text-sm font-semibold text-text-secondary transition-colors hover:bg-accent-light/40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Ver resultado demo
          </Link>
        </main>

        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
