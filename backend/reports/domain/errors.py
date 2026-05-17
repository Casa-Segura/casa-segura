"""Typed errors the report renderer raises (CS-200 AC: explicit error states)."""

from __future__ import annotations


class ReportError(Exception):
    """Base class for report-renderer errors."""

    code = "REPORT_ERROR"


class AnalysisNotFoundError(ReportError):
    code = "ANALYSIS_NOT_FOUND"


class AnalysisNotReadyError(ReportError):
    """Raised when ``ContractAnalysis`` exists but score_total/band are NULL.

    Differentiates "pending" from "not found" so callers (F7 delivery) can
    distinguish bad ID vs queue-not-finished.
    """

    code = "ANALYSIS_NOT_READY"


class AnalysisFailedError(ReportError):
    """Raised when the upstream pipeline marked the analysis failed."""

    code = "ANALYSIS_FAILED"


class VersionMissingError(ReportError):
    """Raised when rubric/corpus/benchmark version is required but absent."""

    code = "VERSION_MISSING"


class TemplateNotFoundError(ReportError):
    code = "TEMPLATE_NOT_FOUND"


class PdfRenderFailedError(ReportError):
    code = "PDF_RENDER_FAILED"


__all__ = [
    "AnalysisFailedError",
    "AnalysisNotFoundError",
    "AnalysisNotReadyError",
    "PdfRenderFailedError",
    "ReportError",
    "TemplateNotFoundError",
    "VersionMissingError",
]
