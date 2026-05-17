"""``generate_report_pdf(analysis_id, options)`` facade (CS-209).

Wraps ``generate_report_html`` then hands the HTML to WeasyPrint. The
WeasyPrint import is lazy so test environments without the native
libs can still import ``reports.*``; the public function raises
``PdfRenderFailedError`` with a clear message when the binary stack
is missing.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from reports.application.metrics import (
    REPORT_BYTES_HISTOGRAM,
    REPORT_PDF_DURATION,
    REPORT_RENDER_OUTCOMES,
)
from reports.application.services.html_renderer import (
    GenerateReportOptions,
    generate_report_html,
)
from reports.domain.errors import PdfRenderFailedError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PdfResult:
    """Outcome of ``generate_report_pdf`` — bytes + observability."""

    pdf_bytes: bytes
    bytes_generated: int
    elapsed_ms: int
    page_size: str


@dataclass(frozen=True)
class PdfOptions:
    """PDF-specific options layered on top of HTML options."""

    page_size: str = "Letter"  # "Letter" | "A4"
    margin_cm: float = 1.5


def generate_report_pdf(
    analysis,
    *,
    html_options: GenerateReportOptions | None = None,
    pdf_options: PdfOptions | None = None,
) -> PdfResult:
    """Render the analysis as HTML and convert to PDF via WeasyPrint."""

    html_options = html_options or GenerateReportOptions()
    pdf_options = pdf_options or PdfOptions()
    html = generate_report_html(analysis, options=html_options)

    try:
        from weasyprint import (  # type: ignore[import-not-found]  # noqa: PLC0415 — lazy: WeasyPrint requires native libs and tests skip when absent
            CSS,
            HTML,
        )
    except Exception as exc:
        raise PdfRenderFailedError(
            "WeasyPrint is not installed or the native libraries are missing on this host"
        ) from exc

    start = time.perf_counter()
    page_css = CSS(string=_build_page_css(pdf_options))
    try:
        pdf_bytes = HTML(string=html).write_pdf(stylesheets=[page_css])
    except Exception as exc:
        REPORT_PDF_DURATION.labels(page_size=pdf_options.page_size, outcome="error").observe(
            time.perf_counter() - start
        )
        REPORT_RENDER_OUTCOMES.labels(format="pdf", outcome="error").inc()
        logger.warning("reports.pdf.weasyprint_failed", exc_info=True)
        raise PdfRenderFailedError(f"WeasyPrint failed: {exc}") from exc
    elapsed_ms = int((time.perf_counter() - start) * 1000)

    REPORT_PDF_DURATION.labels(page_size=pdf_options.page_size, outcome="ok").observe(elapsed_ms / 1000.0)
    REPORT_RENDER_OUTCOMES.labels(format="pdf", outcome="ok").inc()
    REPORT_BYTES_HISTOGRAM.labels(format="pdf").observe(len(pdf_bytes))

    return PdfResult(
        pdf_bytes=pdf_bytes,
        bytes_generated=len(pdf_bytes),
        elapsed_ms=elapsed_ms,
        page_size=pdf_options.page_size,
    )


def _build_page_css(opts: PdfOptions) -> str:
    return f"""
    @page {{
        size: {opts.page_size};
        margin: {opts.margin_cm}cm;

        @top-left {{ content: 'Casa Segura — Análisis de Contrato'; font-size: 9pt; color: #6B7280; }}
        @top-right {{ content: string(public_short_id); font-size: 9pt; color: #6B7280; }}
        @bottom-center {{ content: 'Página ' counter(page) ' de ' counter(pages); font-size: 9pt; color: #6B7280; }}
    }}
    body {{ font-family: Helvetica, Arial, sans-serif; }}
    .cs-watermark {{ position: fixed; opacity: 0.06; font-size: 80pt; color: #10B981; transform: rotate(-25deg); top: 40%; left: 15%; pointer-events: none; }}
    """


__all__ = ["PdfOptions", "PdfResult", "generate_report_pdf"]
