import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ProjectVerificationFlowShell } from "@/components/project-verification-flow-shell";
import { ProjectVerificationBillboardUploadForm } from "@/components/project-verification-billboard-upload-form";
import { cx, focusRing } from "@/components/casa-ui";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer-registry";
import { buildManualVerificationHandoffPath } from "@/lib/project-verification-manual-handoff";

const manualSkipPhotoHref = buildManualVerificationHandoffPath({
  source: "photo_skip",
});

export const metadata: Metadata = {
  title: `Foto de valla — verificación de proyecto — Casa Segura`,
  description: `Captura opcional de valla para verificación de proyecto. ${DISCLAIMER_SHORT}.`,
};

export default function ProjectVerificationBillboardPhotoPage() {
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
        className="flex flex-1 flex-col gap-6 outline-none lg:grid lg:grid-cols-1 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.92fr)] lg:items-start lg:gap-x-10"
      >
        <div className="flex flex-col gap-6">
          <header className="rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-accent">
              Paso 1
            </p>
            <h1 className="mt-2 max-w-xl text-balance text-2xl font-semibold leading-tight tracking-tight text-text-primary">
              Subí una foto clara de la valla
            </h1>
            <p className="mt-3 max-w-xl text-base leading-relaxed text-text-secondary">
              Este camino prepara la lectura automática. Por ahora el stub confirma
              que el archivo llega; después el OCR podrá completar o sugerir los
              campos del formulario manual.
            </p>
          </header>

          <ProjectVerificationBillboardUploadForm />

          <p className="text-center lg:text-start">
            <Link
              href={manualSkipPhotoHref}
              className={cx(
                "inline-flex min-h-[44px] items-center justify-center gap-2 text-sm font-semibold text-accent underline-offset-4 hover:underline",
                focusRing,
                "rounded-[var(--radius-input)] px-2",
              )}
            >
              Ingresar datos manualmente sin foto
            </Link>
          </p>
        </div>

        <aside
          aria-label="Resumen del flujo"
          className="rounded-[var(--radius-card)] border border-border bg-surface p-5 shadow-sm xl:sticky xl:top-6 max-xl:hidden"
        >
          <h2 className="text-sm font-semibold text-text-primary">
            Antes de enviar
          </h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-relaxed text-text-secondary">
            <li>Incluí nombre del proyecto, desarrollador, permiso y dirección visible.</li>
            <li>Buscá buena luz y encuadrá el texto; evitá cortar bordes con datos.</li>
            <li>Podés volver después al formulario manual si el OCR propone valores raros.</li>
          </ul>
        </aside>
      </main>

      <footer className="mt-auto border-t border-border pt-6 pb-2">
        <DisclaimerFooter />
      </footer>
    </ProjectVerificationFlowShell>
  );
}
