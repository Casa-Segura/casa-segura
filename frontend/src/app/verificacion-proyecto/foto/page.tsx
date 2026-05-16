import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ProjectVerificationBillboardUploadForm } from "@/components/project-verification-billboard-upload-form";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";

export const metadata: Metadata = {
  title: `Foto de valla — verificación de proyecto — Casa Segura`,
  description: `Captura opcional de valla para verificación de proyecto. ${DISCLAIMER_SHORT}.`,
};

export default function ProjectVerificationBillboardPhotoPage() {
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
              Paso 1
            </p>
            <h1 className="mt-2 text-balance text-2xl font-semibold leading-tight tracking-tight text-text-primary">
              Subí una foto clara de la valla
            </h1>
            <p className="mt-3 text-base leading-relaxed text-text-secondary">
              Este camino prepara la lectura automática. Por ahora confirma que
              el archivo llega al stub; después el OCR podrá completar o sugerir
              los campos del formulario manual.
            </p>
          </header>

          <ProjectVerificationBillboardUploadForm />
        </main>

        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
