import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";

export default function ProjectVerificationNotFound() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-6 outline-none"
      >
        <h1 className="text-balance text-xl font-semibold text-text-primary">
          Esta sección no está disponible
        </h1>
        <p className="text-base leading-relaxed text-text-secondary">
          La verificación opcional de proyectos o vallas no está habilitada en
          esta instancia. Podés seguir usando el análisis de contratos sin este
          paso.
        </p>
        <Link
          href="/subir"
          className="inline-flex min-h-[44px] max-w-fit items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Ir a analizar un contrato
        </Link>
        <Link
          href="/"
          className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Volver al inicio
        </Link>
      </main>
      <footer className="mx-auto mt-auto w-full max-w-[480px] border-t border-border pt-6 pb-2">
        <DisclaimerFooter />
      </footer>
    </div>
  );
}
