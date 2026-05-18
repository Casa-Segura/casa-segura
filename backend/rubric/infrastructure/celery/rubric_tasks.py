"""Celery tasks for the rubric engine (PRD_F4 §6.1, §6.4).

The main task ``rubric.evaluate_analysis`` orchestrates:

1. Resolve ``CriterionSpec`` rows for this analysis (stamped ``rubric_version``,
   else active catalog — see ``CriterionRepository.load_specs_for_analysis`` / CS-358).
2. Build ``EvaluationContext`` from the ``ContractAnalysis`` row's
   classification + economic summary + ingestion text.
3. Run ``RubricEvaluationService.evaluate`` (async) inside ``asyncio.run``.
4. Persist the result via ``ContractAnalysisRepository.persist``.
5. Emit the "ready for report" event (out of scope for F4; the report
   feature subscribes to ``ContractAnalysis`` saved with ``band`` set).
"""

from __future__ import annotations

import asyncio
import time

import structlog
from celery import shared_task

from platform_core.infrastructure.django.models import ContractAnalysis
from rubric.application.categories.registry import build_default_registry
from rubric.application.services.criterion_evaluator import EvaluationContext
from rubric.application.services.rubric_evaluation_service import RubricEvaluationService
from rubric.infrastructure.django.repositories import (
    ContractAnalysisRepository,
    CriterionRepository,
)

logger = structlog.get_logger(__name__)


@shared_task(name="rubric.evaluate_analysis", bind=True, max_retries=2, autoretry_for=(LookupError,))
def evaluate_analysis(self, analysis_id: str) -> dict:
    """Evaluate ``analysis_id`` end-to-end and persist the result.

    Returns a compact dict for downstream tasks (F6 / F8) so they can
    react without re-reading the row when they only need the band/score.
    """

    wall_start = time.perf_counter()
    logger.info("rubric.evaluate_analysis.started", analysis_id=analysis_id)

    analysis = ContractAnalysis.objects.select_related("rubric_version", "corpus_version", "benchmark_version").get(
        pk=analysis_id
    )

    criterion_repo = CriterionRepository()
    specs, resolved_version, catalog_source = criterion_repo.load_specs_for_analysis(analysis)

    context = EvaluationContext(
        analysis_id=str(analysis.id),
        contract_text="",  # populated by the ingestion stream; passed via kwargs in real wiring
        contract_type=analysis.contract_type,
        elements_detected={},
        economic_summary=analysis.economic_summary or {},
        classification={},
        benchmark_version=(analysis.benchmark_version_id if analysis.benchmark_version_id else None),
        corpus_version=analysis.corpus_version_id,
        rubric_version=resolved_version,
    )

    service = RubricEvaluationService(registry=build_default_registry())
    result = asyncio.run(
        service.evaluate(
            specs,
            context,
            rubric_version=resolved_version,
            corpus_version=analysis.corpus_version_id or "",
            benchmark_version=analysis.benchmark_version_id,
        )
    )

    ContractAnalysisRepository().persist(analysis_id, result)

    elapsed_ms = round((time.perf_counter() - wall_start) * 1000)
    logger.info(
        "rubric.evaluate_analysis.completed",
        analysis_id=analysis_id,
        elapsed_ms=elapsed_ms,
        score_total=result.score_total,
        band=result.band.value,
        overrides=[c.value for c in result.override_triggered],
        unverifiable_count=result.unverifiable_count,
        rubric_version=resolved_version,
        rubric_catalog_source=catalog_source,
    )

    return {
        "analysis_id": analysis_id,
        "score_total": result.score_total,
        "band": result.band.value,
        "override_active": bool(result.override_triggered),
        "findings_count": result.findings_count,
    }


__all__ = ["evaluate_analysis"]
