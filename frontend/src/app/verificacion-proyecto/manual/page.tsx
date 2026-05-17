import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ManualVerificationEntryAssist } from "@/components/manual-verification-entry-assist";
import { ProjectVerificationFlowShell } from "@/components/project-verification-flow-shell";
import { ProjectVerificationManualForm } from "@/components/project-verification-manual-form";
import { DISCLAIMER_SHORT } from "@/legal/disclaimer-registry";
import {
  impliesOcrRecoverySource,
  parseManualVerificationHandoffSearchParams,
} from "@/lib/project-verification-manual-handoff";

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
    ocr_quality?: string;
  }>;
};

export default async function ProjectVerificationManualPage({
  searchParams,
}: ManualPageProps) {
  const sp = (await searchParams) ?? {};
  const { initialValues, source, hasPrefill, ocr_quality: ocrQuality } =
    parseManualVerificationHandoffSearchParams(sp);

  let prefillNote: string | undefined;
  if (hasPrefill) {
    prefillNote =
      impliesOcrRecoverySource(source) || source === "billboard_stub_continue"
        ? "La lectura automática fue incierta o incompleta. Revisá los campos sugeridos antes de enviar y corregí lo que necesites antes de mandar los datos."
        : "Trajimos datos sugeridos desde la lectura de valla. Revisalos antes de enviar; podés corregir cualquier campo.";
  } else if (impliesOcrRecoverySource(source)) {
    prefillNote =
      "Pasaste al formulario manual porque la lectura automática falló. Completá lo que puedas desde la valla o tus recuerdos; después validamos en servidor.";
  }

  return (
    <ProjectVerificationFlowShell>
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

      <ManualVerificationEntryAssist source={source} />

      <main
        id="main-content"
        tabIndex={-1}
        className="flex flex-1 flex-col gap-6 outline-none lg:justify-center"
      >
        <div className="rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-text-primary">
            Datos del proyecto (manual)
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-text-secondary">
            Respaldo cuando la lectura automática de la valla falle. La imagen no
            se guarda: solo usamos estos campos para un veredicto orientativo sin
            persistencia.
          </p>
          <div className="mt-6">
            <ProjectVerificationManualForm
              initialValues={initialValues}
              prefillNote={prefillNote}
              verificationMeta={
                source === "verification_hub" ||
                source === "photo_skip" ||
                !source
                  ? { submissionSource: "manual" }
                  : {
                      submissionSource: "billboard_ocr",
                      ocrQuality,
                    }
              }
            />
          </div>
        </div>
      </main>

      <footer className="mt-auto border-t border-border pt-6 pb-2">
        <DisclaimerFooter />
      </footer>
    </ProjectVerificationFlowShell>
  );
}
