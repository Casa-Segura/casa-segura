import Link from "next/link";
import { redirect } from "next/navigation";
import { DisclaimerFooter } from "@/components/disclaimer-footer";
import { ReportPublicFrame } from "@/components/report-public-frame";
import { buildPublicReportUrl } from "@/server/contract-env";

/**
 * CS-294 — probes BE HTML once, then embeds via sandboxed iframe `src` (same URL) for correct relative assets.
 *
 * Expired / missing report (CS-295): redirects to `/enlace-expirado` when —
 * `buildPublicReportUrl` is null (malformed/missing short id or missing API base),
 * BE returns HTTP 404 or 410,
 * Fetch is a 3xx without following (manual redirect handling),
 * response is non-OK,
 * `Content-Type` is not HTML (or XHTML).
 */

type PageProps = {
  params: Promise<{ publicShortId: string }>;
  searchParams: Promise<{ anonymized?: string; expires?: string }>;
};

function formatExpiresForDisplay(raw: string): string {
  const t = Date.parse(raw);
  if (!Number.isFinite(t)) return raw;
  try {
    return new Intl.DateTimeFormat("es-SV", {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(t));
  } catch {
    return raw;
  }
}

export default async function PublicReportPage({
  params,
  searchParams,
}: PageProps) {
  const { publicShortId } = await params;
  const sp = await searchParams;
  const url = buildPublicReportUrl(publicShortId);

  if (!url) {
    redirect("/enlace-expirado");
  }

  const res = await fetch(url, {
    cache: "no-store",
    headers: {
      Accept: "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    },
    redirect: "manual",
  });

  if (res.status === 404 || res.status === 410) {
    redirect("/enlace-expirado");
  }
  if (res.status >= 300 && res.status < 400) {
    redirect("/enlace-expirado");
  }
  if (!res.ok) {
    redirect("/enlace-expirado");
  }

  const htmlContentType = res.headers.get("content-type")?.toLowerCase() ?? "";
  if (
    htmlContentType &&
    !htmlContentType.includes("text/html") &&
    !htmlContentType.includes("application/xhtml")
  ) {
    redirect("/enlace-expirado");
  }

  const anonymized = sp.anonymized === "1" || sp.anonymized === "true";
  const expiresLabel = sp.expires?.trim()
    ? formatExpiresForDisplay(sp.expires.trim())
    : null;

  return (
    <div className="flex min-h-dvh flex-col bg-bg px-4 py-6 print:bg-white sm:px-6">
      <div className="mx-auto flex w-full max-w-[480px] flex-1 flex-col gap-5 print:max-w-none">
        <Link
          href="/"
          className="text-sm font-medium text-accent underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent print:hidden"
        >
          Volver al inicio
        </Link>

        <main
          id="main-content"
          tabIndex={-1}
          className="flex min-w-0 flex-1 flex-col gap-5 outline-none print:gap-4"
        >
          <header className="shrink-0 print:shrink">
            <h1 className="text-xl font-semibold text-text-primary">
              Tu informe
            </h1>
            <p className="mt-2 break-words font-mono text-sm text-text-secondary">
              ID corto: {publicShortId}
            </p>
            {expiresLabel ? (
              <p className="mt-2 text-sm text-text-secondary">
                Enlace vence aproximadamente el {expiresLabel} (hora local).
              </p>
            ) : null}
            {anonymized ? (
              <p className="mt-2 rounded-[var(--radius-input)] border border-border bg-verdict-yellow-bg px-3 py-2 text-sm text-text-primary">
                Estás viendo la versión anonimizada del informe (puede omitir
                datos sensibles a propósito).
              </p>
            ) : null}
          </header>

          <div className="min-w-0 flex-1 overflow-x-auto print:overflow-visible print:max-w-none">
            <ReportPublicFrame
              src={url}
              title={`Informe de análisis ${publicShortId}`}
            />
          </div>
        </main>

        <footer className="mt-auto shrink-0 border-t border-border pt-6 print:pt-4">
          <DisclaimerFooter />
        </footer>
      </div>
    </div>
  );
}
