"""Celery surface for report generation (PRD F6 §6.2)."""

from __future__ import annotations

import structlog
from celery import shared_task

from platform_core.infrastructure.django.models import ContractAnalysis
from reports.application.services.html_renderer import (
    GenerateReportOptions,
    generate_report_html,
)
from reports.application.services.pdf_renderer import (
    PdfOptions,
    PdfResult,
    generate_report_pdf,
)

logger = structlog.get_logger(__name__)


@shared_task(name="reports.generate_html", bind=True, max_retries=1)
def generate_html_task(self, analysis_id: str) -> dict:
    """Render the report HTML for ``analysis_id`` and return its size."""

    analysis = ContractAnalysis.objects.select_related("project").get(pk=analysis_id)
    project_name = analysis.project.canonical_name if analysis.project_id else None
    html = generate_report_html(
        analysis,
        options=GenerateReportOptions(project_name=project_name),
    )
    logger.info("reports.generate_html.ok", analysis_id=analysis_id, bytes=len(html))
    return {"analysis_id": analysis_id, "bytes": len(html)}


@shared_task(name="reports.generate_pdf", bind=True, max_retries=1)
def generate_pdf_task(self, analysis_id: str) -> dict:
    """Render the PDF; F7 delivery picks the bytes from this task."""

    analysis = ContractAnalysis.objects.select_related("project").get(pk=analysis_id)
    project_name = analysis.project.canonical_name if analysis.project_id else None
    result: PdfResult = generate_report_pdf(
        analysis,
        html_options=GenerateReportOptions(project_name=project_name),
        pdf_options=PdfOptions(),
    )
    logger.info(
        "reports.generate_pdf.ok",
        analysis_id=analysis_id,
        bytes=result.bytes_generated,
        elapsed_ms=result.elapsed_ms,
    )
    return {
        "analysis_id": analysis_id,
        "bytes": result.bytes_generated,
        "elapsed_ms": result.elapsed_ms,
        "page_size": result.page_size,
    }


__all__ = ["generate_html_task", "generate_pdf_task"]
