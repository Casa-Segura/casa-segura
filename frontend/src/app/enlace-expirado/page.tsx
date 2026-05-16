import type { Metadata } from "next";
import Link from "next/link";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import {
  EXPIRED_ANALYSIS_PRIVACY_LINE,
  EXPIRED_ANALYSIS_UNAVAILABLE,
} from "@/legal/expired-link-copy";

/** PRD_GENERAL US-05 — expired delivery link UX (CS-295). No third-party telemetry on this route. */

export const metadata: Metadata = {
  title: "Enlace no disponible · Casa Segura",
  robots: { index: false, follow: false },
};

export default function EnlaceExpiradoPage() {
  return (
    <div className="flex min-h-dvh flex-1 flex-col bg-bg px-4 py-6 sm:px-6">
      <div className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-6">
        <Link
          href="/"
          className="inline-flex max-w-fit min-h-[44px] items-center justify-center rounded-[var(--radius-input)] px-3 py-2 text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
        >
          Volver al inicio
        </Link>
        <main
          id="main-content"
          tabIndex={-1}
          className="flex min-w-0 flex-1 flex-col gap-4 rounded-[var(--radius-card)] border border-border bg-surface p-6 shadow-sm outline-none"
        >
          <h1 className="break-words text-xl font-semibold text-text-primary">
            {EXPIRED_ANALYSIS_UNAVAILABLE}
          </h1>
          <p className="break-words text-base leading-relaxed text-text-secondary">
            {EXPIRED_ANALYSIS_PRIVACY_LINE}
          </p>
          <p className="break-words text-base leading-relaxed text-text-secondary">
            Si acabás de abrir el enlace y ves este mensaje, puede haber un
            retraso puntual: intentá de nuevo en unos minutos o iniciá un
            análisis nuevo.
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
