"""Narrow ports for EPIC-07 PDF/HTML generators."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReportPdfGeneratorPort(Protocol):
    """Substituted by real F6 renderer."""

    def generate_pdf_bytes(self, *, analysis_id: str) -> bytes:
        """Return PDF bytes for attachment."""
