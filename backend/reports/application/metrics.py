"""Prometheus instrumentation for the report generation surface — CS-330."""

from __future__ import annotations

from shared.observability.metrics import safe_counter, safe_histogram

REPORT_HTML_DURATION = safe_histogram(
    "casa_segura_report_html_duration_seconds",
    "HTML report rendering latency.",
    labelnames=("template_version", "outcome"),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

REPORT_PDF_DURATION = safe_histogram(
    "casa_segura_report_pdf_duration_seconds",
    "PDF report rendering latency (WeasyPrint).",
    labelnames=("page_size", "outcome"),
    buckets=(0.1, 0.25, 0.5, 1, 2, 3, 5, 7.5, 10, 15, 30),
)

REPORT_RENDER_OUTCOMES = safe_counter(
    "casa_segura_report_render_outcomes_total",
    "Counter of report renders by format and outcome.",
    labelnames=("format", "outcome"),
)

REPORT_BYTES_HISTOGRAM = safe_histogram(
    "casa_segura_report_bytes",
    "Histogram of rendered report payload size.",
    labelnames=("format",),
    buckets=(50_000, 100_000, 200_000, 400_000, 800_000, 1_600_000, 3_200_000),
)


__all__ = [
    "REPORT_BYTES_HISTOGRAM",
    "REPORT_HTML_DURATION",
    "REPORT_PDF_DURATION",
    "REPORT_RENDER_OUTCOMES",
]
