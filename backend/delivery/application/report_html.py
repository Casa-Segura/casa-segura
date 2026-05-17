"""On-demand HTML report synthesis — CS-247 (no persistence, BR-01)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from django.utils import timezone

from ingestion.domain.enums import ProcessingStatus
from platform_core.infrastructure.django.models import ContractAnalysis

logger = logging.getLogger(__name__)

MAX_INFO_SNIPPET = 64


class ReportNotFound(LookupError):
    """Mapped to HTTP 404 for public/report ports."""


class AnalysisNotReady(ValueError):
    """Analysis exists but rubric/output not ready for rendering."""


@dataclass(frozen=True, slots=True)
class RenderStats:
    duration_ms: float
    byte_length: int


def generate_report_html_for_analysis(
    *,
    public_short_id: str | None = None,
    analysis_id: str | None = None,
) -> tuple[str, RenderStats]:
    """Return ephemeral HTML + timing stats — does not touch disk (CS-247)."""

    sid = (public_short_id or "").strip()
    aid = (analysis_id or "").strip()
    if not sid and not aid:
        raise ReportNotFound("missing_identifier")

    if sid:
        analysis = ContractAnalysis.objects.filter(public_short_id=sid).first()
    else:
        analysis = ContractAnalysis.objects.filter(pk=aid).first()

    if analysis is None:
        raise ReportNotFound("analysis_not_found")

    sub = analysis.submissions.order_by("-pk").first()
    if sub is not None and sub.processing_status != ProcessingStatus.COMPLETED.value:
        raise AnalysisNotReady("analysis_pending")

    t0 = time.perf_counter()
    # Stub until EPIC-07 wires F6 — deterministic, byte-stable for tests.
    band = analysis.band or "pendiente"
    score = analysis.score_total or ""
    html = (
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"/>'
        '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
        "<title>Casa Segura</title></head><body>"
        f"<main><h1>Informe {analysis.public_short_id}</h1>"
        f"<p>Puntuación: {score} — banda: {band}.</p>"
        "<p>Vista regenerada bajo demanda; no se almacena HTML intermedio (BR-01).</p>"
        "</main></body></html>"
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    snippet = html[:MAX_INFO_SNIPPET]
    logger.info(
        "report_html_generated",
        extra={
            "public_short_id": analysis.public_short_id,
            "byte_length": len(html.encode("utf-8")),
            "snippet_prefix": snippet,
            "generated_at": timezone.now().isoformat(),
        },
    )
    return html, RenderStats(duration_ms=elapsed_ms, byte_length=len(html.encode("utf-8")))
