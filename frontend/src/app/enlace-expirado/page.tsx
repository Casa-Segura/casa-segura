import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";

/** Minimal expired-link surface (CS-294 handoff); full CS-295 copy/telemetry may extend this route. */
export default function EnlaceExpiradoPage() {
  return (
    <div className="flex min-h-dvh flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-6">
        <Link
          href="/"
          className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Volver al inicio
        </Link>
        <main className="flex flex-1 flex-col gap-4 rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm">
          <h1 className="text-xl font-semibold text-text-primary">
            Este enlace ya no está disponible
          </h1>
          <p className="text-base leading-relaxed text-text-secondary">
            Por privacidad, los informes caducan después de un tiempo. Si acabas de abrir el enlace y ves
            este mensaje, puede haber un retraso puntual: vuelve a intentarlo en unos minutos o sube de nuevo tu contrato.
          </p>
          <Link
            href="/subir"
            className="mt-2 flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-center text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            Empezar un análisis nuevo
          </Link>
        </main>
        <footer className="mt-auto border-t border-border pt-6 pb-2">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
