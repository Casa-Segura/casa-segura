"""On-demand HTML report synthesis — CS-247 (no persistence, BR-01)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from django.utils import timezone

from ingestion.domain.enums import ProcessingStatus
from platform_core.infrastructure.django.models import ContractAnalysis
from reports.application.services.html_renderer import (
    GenerateReportOptions,
    generate_report_html,
)
from reports.domain.errors import (
    AnalysisFailedError,
    AnalysisNotFoundError,
    AnalysisNotReadyError,
    ReportError,
)

logger = logging.getLogger(__name__)


class ReportNotFound(LookupError):
    """Mapped to HTTP 404 for public/report ports."""


class AnalysisNotReady(ValueError):
    """Analysis exists but rubric/output not ready for rendering."""


class ReportRenderFailed(RuntimeError):
    """Canonical renderer failed (misconfiguration / unexpected). Maps to HTTP 500."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True, slots=True)
class RenderStats:
    duration_ms: float
    byte_length: int


def _load_analysis_with_project(
    *,
    public_short_id: str | None,
    analysis_id: str | None,
    analysis: ContractAnalysis | None,
) -> ContractAnalysis:
    """Return ``ContractAnalysis`` with ``project`` prefetched."""
    base = ContractAnalysis.objects.select_related("project")
    if analysis is not None:
        row = base.filter(pk=analysis.pk).first()
        if row is None:
            raise ReportNotFound("analysis_not_found")
        sid = (public_short_id or "").strip()
        if sid and row.public_short_id != sid:
            raise ReportNotFound("analysis_not_found")
        return row

    sid = (public_short_id or "").strip()
    aid = (analysis_id or "").strip()
    if not sid and not aid:
        raise ReportNotFound("missing_identifier")

    if sid:
        row = base.filter(public_short_id=sid).first()
    else:
        row = base.filter(pk=aid).first()
    if row is None:
        raise ReportNotFound("analysis_not_found")
    return row


def generate_report_html_for_analysis(
    *,
    public_short_id: str | None = None,
    analysis_id: str | None = None,
    analysis: ContractAnalysis | None = None,
) -> tuple[str, RenderStats]:
    """Return ephemeral HTML + timing stats — does not touch disk (CS-247)."""

    loaded = _load_analysis_with_project(
        public_short_id=public_short_id,
        analysis_id=analysis_id,
        analysis=analysis,
    )

    sub = loaded.submissions.order_by("-pk").first()
    if sub is not None and sub.processing_status != ProcessingStatus.COMPLETED.value:
        raise AnalysisNotReady("analysis_pending")

    project_name = loaded.project.canonical_name if loaded.project_id else None
    options = GenerateReportOptions(project_name=project_name)

    t0 = time.perf_counter()
    try:
        html = generate_report_html(loaded, options=options)
    except AnalysisNotFoundError as exc:
        logger.info(
            "report_html_analysis_not_found",
            extra={
                "public_short_id": loaded.public_short_id,
                "error": exc.__class__.__name__,
                "code": exc.code,
            },
        )
        raise ReportNotFound("analysis_not_found") from exc
    except (AnalysisNotReadyError, AnalysisFailedError) as exc:
        logger.info(
            "report_html_analysis_not_ready",
            extra={
                "public_short_id": loaded.public_short_id,
                "error": exc.__class__.__name__,
                "code": exc.code,
            },
        )
        raise AnalysisNotReady("analysis_not_ready") from exc
    except ReportError as exc:
        logger.error(
            "report_html_renderer_failed",
            extra={
                "public_short_id": loaded.public_short_id,
                "error": exc.__class__.__name__,
                "code": exc.code,
            },
        )
        raise ReportRenderFailed(exc.code, code=exc.code) from exc

    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    raw = html.encode("utf-8")
    byte_length = len(raw)
    logger.info(
        "report_html_generated",
        extra={
            "public_short_id": loaded.public_short_id,
            "byte_length": byte_length,
            "duration_ms": round(elapsed_ms, 3),
            "generated_at": timezone.now().isoformat(),
        },
    )
    return html, RenderStats(duration_ms=elapsed_ms, byte_length=byte_length)
