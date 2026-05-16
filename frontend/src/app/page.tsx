import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <main className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-[var(--spacing-section)]">
        <header className="shrink-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">
            Casa Segura
          </p>
        </header>

        <section className="flex flex-1 flex-col gap-5">
          <h1 className="text-[1.625rem] font-semibold leading-snug tracking-tight text-text-primary sm:text-3xl">
            Analiza tu contrato de vivienda antes de firmar
          </h1>
          <p className="text-base leading-relaxed text-text-secondary">
            Sube el PDF o las fotos y recibe un informe claro sobre cláusulas
            repetidas, avisos y riesgos típicos. Tú decides con más contexto;
            no validamos proyectos ni vallas publicitarias para empezar.
          </p>

          <div className="mt-2 flex flex-col gap-3">
            <Link
              href="/subir"
              className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-center text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 active:opacity-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Revisar mi contrato
            </Link>
            <p className="text-center text-sm text-text-secondary">
              En menos de dos minutos. Funciona en el móvil.
            </p>
          </div>
        </section>

        <footer className="mt-auto shrink-0 border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </main>
    </div>
  );
}
