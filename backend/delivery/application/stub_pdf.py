"""Stub PDF generator until EPIC-07 wires real renderer."""

from __future__ import annotations

from delivery.application.ports import ReportPdfGeneratorPort


class StubReportPdfGenerator(ReportPdfGeneratorPort):
    """Minimal valid PDF for integration tests."""

    _PDF_MAGIC = b"%PDF-1.4\n1 0 obj<<>>endobj trailer<<>>\n%%EOF\n"

    def generate_pdf_bytes(self, *, analysis_id: str) -> bytes:
        _ = analysis_id
        return self._PDF_MAGIC
