import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ProjectVerificationManualForm } from "@/components/project-verification-manual-form";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer";

export const metadata: Metadata = {
  title: `Formulario manual — verificación de proyecto — Casa Segura`,
  description: `Datos estructurados para verificación opcional. ${DISCLAIMER_SHORT}.`,
};

type ManualPageProps = {
  searchParams?: Promise<{
    developer?: string;
    project?: string;
    permit?: string;
    address?: string;
    source?: string;
  }>;
};

function cleanParam(value: string | undefined): string | undefined {
  const clean = value?.trim();
  return clean ? clean.slice(0, 240) : undefined;
}

export default async function ProjectVerificationManualPage({
  searchParams,
}: ManualPageProps) {
  const sp = (await searchParams) ?? {};
  const initialValues = {
    developer: cleanParam(sp.developer),
    project: cleanParam(sp.project),
    permit: cleanParam(sp.permit),
    address: cleanParam(sp.address),
  };
  const hasPrefill = Object.values(initialValues).some(Boolean);
  const prefillNote = hasPrefill
    ? "Trajimos datos sugeridos desde la lectura de valla. Revisalos antes de enviar; podés corregir cualquier campo."
    : undefined;

  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:gap-4">
          <Link
            href="/verificacion-proyecto"
            className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Volver a verificación
          </Link>
          <Link
            href="/"
            className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Inicio
          </Link>
        </div>

        <main
          id="main-content"
          tabIndex={-1}
          className="flex flex-1 flex-col rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm outline-none"
        >
          <h1 className="text-xl font-semibold text-text-primary">
            Datos del proyecto
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-text-secondary">
            Flujo de respaldo cuando la lectura automática de valla falle más
            adelante. Hoy solo validamos en el servidor sin guardar datos.
          </p>
          <div className="mt-6">
            <ProjectVerificationManualForm
              initialValues={initialValues}
              prefillNote={prefillNote}
            />
          </div>
        </main>

        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
