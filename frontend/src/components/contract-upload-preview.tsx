"use client";

import Image from "next/image";
import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { CaretLeft, CaretRight } from "@phosphor-icons/react";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

import { CasaButton, SkeletonBlock, cx, focusRing } from "@/components/casa-ui";
import type { ContractUploadPreviewProps } from "@/components/contract-upload-preview.helpers";

let pdfWorkerConfigured = false;

function ensurePdfWorker() {
  if (pdfWorkerConfigured || typeof window === "undefined") return;
  pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
  pdfWorkerConfigured = true;
}

export function ContractUploadPreview({
  kind,
  objectUrl,
  fileName,
  density = "comfortable",
  fillParent = false,
  className,
}: ContractUploadPreviewProps) {
  ensurePdfWorker();

  const regionId = useId();
  const announceRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(280);

  const [pdfPage, setPdfPage] = useState(1);
  const [pdfNumPages, setPdfNumPages] = useState<number | null>(null);
  const [pdfLoadError, setPdfLoadError] = useState<string | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => {
      const w = el.clientWidth;
      setContainerWidth(Math.max(160, Math.min(w - 24, 560)));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const onPdfLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setPdfNumPages(numPages);
    setPdfLoadError(null);
  }, []);

  const onPdfLoadError = useCallback(() => {
    setPdfLoadError(
      "No pudimos mostrar este PDF en el navegador. Podés enviarlo igual; el servidor intentará leerlo.",
    );
    setPdfNumPages(null);
  }, []);

  const announcePage = useCallback((page: number, total: number | null) => {
    const el = announceRef.current;
    if (!el) return;
    el.textContent =
      total != null
        ? `Página ${page} de ${total}`
        : `Página ${page}`;
  }, []);

  useEffect(() => {
    if (kind !== "pdf" || pdfNumPages == null) return;
    announcePage(pdfPage, pdfNumPages);
  }, [kind, pdfPage, pdfNumPages, announcePage]);

  const maxHeightClass = fillParent
    ? "min-h-0 flex-1 overflow-hidden"
    : density === "compact"
      ? "max-h-[min(45vh,360px)] lg:max-h-[min(50vh,420px)]"
      : "max-h-[min(50vh,420px)] sm:max-h-[min(55vh,480px)] lg:max-h-[min(60vh,520px)]";

  const alt = `Vista previa del archivo seleccionado: ${fileName}`;

  return (
    <section
      ref={containerRef}
      id={regionId}
      role="region"
      aria-label="Vista previa del contrato"
      className={cx(
        "flex flex-col overflow-hidden rounded-[var(--radius-card)] border border-border bg-surface shadow-[var(--shadow-soft)]",
        fillParent && "flex-1",
        maxHeightClass,
        className,
      )}
    >
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-border bg-surface-muted px-3 py-2">
        <p className="min-w-0 truncate text-xs font-medium text-text-secondary" title={fileName}>
          {kind === "pdf" ? "PDF · " : "Imagen · "}
          {fileName}
        </p>
        {kind === "pdf" && pdfNumPages != null ? (
          <span className="shrink-0 tabular-nums text-xs text-text-secondary" aria-hidden>
            {pdfPage}/{pdfNumPages}
          </span>
        ) : null}
      </header>

      <div
        ref={announceRef}
        className="sr-only"
        aria-live="polite"
      />

      <div className="min-h-0 flex-1 overflow-auto p-3 touch-manipulation">
        {kind === "image" ? (
          <div className="relative mx-auto w-full max-w-[560px]">
            <Image
              src={objectUrl}
              alt={alt}
              width={1120}
              height={800}
              unoptimized
              sizes="(max-width: 768px) 100vw, 560px"
              className="h-auto w-full rounded-[var(--radius-input)] object-contain"
            />
          </div>
        ) : pdfLoadError ? (
          <p className="text-sm leading-relaxed text-text-secondary" role="status">
            {pdfLoadError}
          </p>
        ) : (
          <div className="flex flex-col items-stretch gap-3">
            <Document
              file={objectUrl}
              loading={
                <div className="space-y-2" aria-busy="true">
                  <SkeletonBlock className="h-4 w-3/5" label="Cargando PDF" />
                  <SkeletonBlock className="h-48 w-full" label="Cargando página" />
                  <SkeletonBlock className="h-4 w-4/5" label="Cargando PDF" />
                </div>
              }
              onLoadSuccess={onPdfLoadSuccess}
              onLoadError={onPdfLoadError}
              className="flex justify-center"
            >
              {pdfNumPages != null ? (
                <Page
                  pageNumber={pdfPage}
                  width={containerWidth}
                  renderTextLayer
                  renderAnnotationLayer
                  className="shadow-sm"
                />
              ) : null}
            </Document>

            {pdfNumPages != null && pdfNumPages > 1 ? (
              <div className="flex flex-wrap items-center justify-center gap-2 border-t border-border pt-3">
                <CasaButton
                  type="button"
                  variant="secondary"
                  className={cx("min-h-[44px] px-3 text-sm", focusRing)}
                  disabled={pdfPage <= 1}
                  aria-label="Página anterior"
                  onClick={() =>
                    setPdfPage((p) => {
                      const next = Math.max(1, p - 1);
                      queueMicrotask(() =>
                        announcePage(next, pdfNumPages),
                      );
                      return next;
                    })
                  }
                >
                  <CaretLeft size={18} aria-hidden />
                  Anterior
                </CasaButton>
                <CasaButton
                  type="button"
                  variant="secondary"
                  className={cx("min-h-[44px] px-3 text-sm", focusRing)}
                  disabled={pdfPage >= pdfNumPages}
                  aria-label="Página siguiente"
                  onClick={() =>
                    setPdfPage((p) => {
                      const next = Math.min(pdfNumPages, p + 1);
                      queueMicrotask(() =>
                        announcePage(next, pdfNumPages),
                      );
                      return next;
                    })
                  }
                >
                  Siguiente
                  <CaretRight size={18} aria-hidden />
                </CasaButton>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </section>
  );
}

export default ContractUploadPreview;
