"use client";

import Link from "next/link";
import { useEffect, useRef, useSyncExternalStore } from "react";

import { recordProjectVerificationContractCtaImpression } from "@/app/verificacion-proyecto/resultado/telemetry-actions";

const STORAGE_KEY = "cs.pv.dismissContractCta:v1";

const DISMISS_EVENT = "cs-pv-dismiss-cta";

function subscribe(onStoreChange: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const notify = () => onStoreChange();
  window.addEventListener(DISMISS_EVENT, notify);
  return () => window.removeEventListener(DISMISS_EVENT, notify);
}

function dismissedSnapshot(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.sessionStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

/** SSR + first client paint: show CTA until storage is read (`useSyncExternalStore` hydrates mismatch safely). */
const serverDismissedFallback = (): boolean => false;

/**
 * Secondary optional path to `/subir` — can be dismissed for the tab session so the flow stays skippable (CS-355).
 */
export function ProjectVerificationOptionalContractCta() {
  const dismissed = useSyncExternalStore(
    subscribe,
    dismissedSnapshot,
    serverDismissedFallback,
  );

  const rootRef = useRef<HTMLDivElement>(null);
  const impressionRecorded = useRef(false);

  useEffect(() => {
    if (
      dismissed ||
      typeof IntersectionObserver === "undefined" ||
      typeof window === "undefined"
    )
      return;
    const el = rootRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (impressionRecorded.current) return;
        if (!entries.some((e) => e.isIntersecting)) return;
        impressionRecorded.current = true;
        observer.disconnect();
        void recordProjectVerificationContractCtaImpression();
      },
      { threshold: 0.2 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [dismissed]);

  if (dismissed) return null;

  function dismiss(): void {
    try {
      window.sessionStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* ignore quota / private mode */
    }
    window.dispatchEvent(new Event(DISMISS_EVENT));
  }

  return (
    <div
      ref={rootRef}
      className="flex flex-col gap-3 rounded-[var(--radius-card)] border border-border bg-surface p-4 shadow-sm"
    >
      <p className="text-sm leading-relaxed text-text-secondary">
        Si ya tenés un borrador, podés seguir con el análisis de contratos
        cuando quieras. Es independiente de esta verificación.
      </p>
      <Link
        href="/subir"
        className="flex min-h-[44px] w-full items-center justify-center rounded-[var(--radius-input)] bg-accent px-4 py-3 text-center text-base font-semibold text-white shadow-sm transition-opacity hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        Analizar un contrato (opcional)
      </Link>
      <button
        type="button"
        onClick={dismiss}
        className="min-h-[44px] w-full rounded-[var(--radius-input)] border border-border bg-surface px-4 py-2 text-sm font-semibold text-text-primary shadow-sm transition-colors hover:bg-surface-muted focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        Ocultar sugerencia en esta pestaña
      </button>
    </div>
  );
}
