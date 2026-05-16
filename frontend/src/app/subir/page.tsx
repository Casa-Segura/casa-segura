import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";

/**
 * Placeholder for CS-291 (contract upload + disclaimer gate).
 * CTA on the landing page targets this route per CS-290 acceptance criteria.
 */
export default function SubirContratoPage() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-6">
        <Link
          href="/"
          className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Volver al inicio
        </Link>
        <main className="flex flex-1 flex-col gap-3 rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-text-primary">
            Subir contrato
          </h1>
          <p className="text-base leading-relaxed text-text-secondary">
            Esta pantalla mostrará la subida de archivos y el aviso legal
            (CS-291). Mientras tanto, vuelve al inicio o espera a que
            conectemos la API.
          </p>
        </main>
        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
