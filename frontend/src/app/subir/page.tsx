"use client";

import Link from "next/link";
import { useState } from "react";
import { DisclaimerCallout } from "@/components/disclaimer-callout";
import { DisclaimerFooter } from "@/components/disclaimer-footer";

/**
 * Placeholder for CS-291 (contract upload + disclaimer gate).
 * CTA on the landing page targets this route per CS-290 acceptance criteria.
 */
export default function SubirContratoPage() {
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);

  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-6">
        <Link
          href="/"
          className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Volver al inicio
        </Link>
        <main className="flex flex-1 flex-col gap-5 rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-text-primary">
            Subir contrato
          </h1>
          <p className="text-base leading-relaxed text-text-secondary">
            Esta pantalla mostrará la subida de archivos (CS-291). Mientras tanto,
            confirma el aviso legal para continuar cuando activemos la API.
          </p>

          <DisclaimerCallout
            variant="gate"
            accepted={disclaimerAccepted}
            onAcceptedChange={setDisclaimerAccepted}
          />

          <button
            type="button"
            disabled={!disclaimerAccepted}
            className="flex min-h-11 w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-center text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Continuar
          </button>
        </main>
        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
