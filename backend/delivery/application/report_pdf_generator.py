"""Adapter from F7 delivery to F6 PDF renderer (EPIC-07).

Implements ``ReportPdfGeneratorPort`` by loading the ``ContractAnalysis``
row and handing it to ``reports.application.services.pdf_renderer``
(WeasyPrint). Replaces the historical ``StubReportPdfGenerator`` once
the F6 epic lands.
"""

from __future__ import annotations

import structlog

from delivery.application.ports import ReportPdfGeneratorPort
from platform_core.infrastructure.django.models import ContractAnalysis
from reports.application.services.html_renderer import GenerateReportOptions
from reports.application.services.pdf_renderer import (
    PdfOptions,
    generate_report_pdf,
)

logger = structlog.get_logger(__name__)


class ContractReportPdfGenerator(ReportPdfGeneratorPort):
    """Production F6 → F7 adapter (CS-209)."""

    def __init__(
        self,
        *,
        html_options: GenerateReportOptions | None = None,
        pdf_options: PdfOptions | None = None,
    ) -> None:
        self._html_options = html_options or GenerateReportOptions()
        self._pdf_options = pdf_options or PdfOptions()

    def generate_pdf_bytes(self, *, analysis_id: str) -> bytes:
        analysis = ContractAnalysis.objects.select_related("project").get(pk=analysis_id)
        html_options = self._html_options
        project_name = analysis.project.canonical_name if analysis.project_id else None
        if project_name and not html_options.project_name:
            # Carry the project name through so the report header / footer
            # show the canonical name F4 stamped.
            html_options = GenerateReportOptions(
                template_version=html_options.template_version,
                findings_collapse_threshold=html_options.findings_collapse_threshold,
                art_1686_warning_mode=html_options.art_1686_warning_mode,
                project_name=project_name,
                project_aggregate_note=html_options.project_aggregate_note,
                lawyer_items=html_options.lawyer_items,
                lawyer_fallback_used=html_options.lawyer_fallback_used,
            )
        result = generate_report_pdf(
            analysis,
            html_options=html_options,
            pdf_options=self._pdf_options,
        )
        logger.info(
            "delivery.pdf_generated",
            analysis_id=analysis_id,
            bytes=result.bytes_generated,
            elapsed_ms=result.elapsed_ms,
            page_size=result.page_size,
        )
        return result.pdf_bytes


__all__ = ["ContractReportPdfGenerator"]
