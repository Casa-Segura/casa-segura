"""End-to-end rubric evaluation orchestrator.

Glues every Phase 4 component together:

1. Accept caller-resolved ``CriterionSpec`` rows and rubric version string.
2. Dispatch evaluators via ``CriterionDispatcher`` (CS-158).
3. Aggregate scores + band via ``score_calculator.aggregate_total``
   (CS-152 / CS-156 / CS-157).
4. Build findings + RAG-backed citations (CS-164).
5. Run synthesis + validator (CS-165 / CS-166).
6. Emit ``FullAnalysisResult`` ready for persistence.

The service is async because the dispatcher is async; the Celery task
wraps it with ``asyncio.run``.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from rubric.application.services.criterion_evaluator import (
    CriterionDispatcher,
    CriterionRegistry,
    CriterionSpec,
    EvaluationContext,
)
from rubric.application.services.finding_factory import (
    LegalCitationFetcher,
    build_findings,
    count_critical,
)
from rubric.application.services.score_calculator import aggregate_total
from rubric.application.services.synthesis import (
    SynthesisCallable,
    SynthesisInputs,
    collect_allowed_anchors,
    synthesize,
)
from rubric.application.services.unverifiable import count_unverifiable
from rubric.domain.band import Band
from rubric.domain.entities import FullAnalysisResult


@dataclass
class RubricEvaluationService:
    """Stateless orchestrator — every field is an injected dependency."""

    registry: CriterionRegistry
    dispatcher_factory: Any = CriterionDispatcher
    legal_fetcher: LegalCitationFetcher | None = None
    synthesis_llm: SynthesisCallable | None = None

    async def evaluate(
        self,
        specs: list[CriterionSpec],
        context: EvaluationContext,
        *,
        rubric_version: str,
        corpus_version: str,
        benchmark_version: str | None = None,
    ) -> FullAnalysisResult:
        dispatcher = self.dispatcher_factory(self.registry)
        evaluations = await dispatcher.evaluate_all(specs, context)

        aggregation = aggregate_total(evaluations, contract_type=context.contract_type)

        anchors_by_criterion = {spec.criterion_id: spec.legal_anchor for spec in specs}
        findings = build_findings(
            evaluations,
            legal_anchor_lookup=anchors_by_criterion,
            fetcher=self.legal_fetcher,
        )

        allowed_anchors = collect_allowed_anchors(findings)
        synthesis_inputs = SynthesisInputs(
            contract_type=context.contract_type,
            band=aggregation.band,
            score_total=aggregation.score_total,
            override_codes=aggregation.override_triggered,
            critical_findings_count=count_critical(findings),
            red_findings_count=sum(1 for f in findings if f.severity.value == "red"),
            overcost_vs_benchmark_usd=None,
        )
        synthesis = synthesize(
            synthesis_inputs,
            llm_callable=self.synthesis_llm,
            allowed_anchors=allowed_anchors,
        )

        return FullAnalysisResult(
            score_total=aggregation.score_total,
            band=aggregation.band,
            override_triggered=list(aggregation.override_triggered),
            scores_by_category=list(aggregation.category_scores),
            criterion_evaluations=[ev for ev in evaluations if ev.applicable],
            findings=findings,
            findings_count=len(findings),
            critical_findings_count=count_critical(findings),
            unverifiable_count=count_unverifiable(evaluations),
            executive_summary=synthesis.summary,
            rubric_version=rubric_version,
            corpus_version=corpus_version,
            benchmark_version=benchmark_version,
        )

    def evaluate_sync(
        self,
        specs: list[CriterionSpec],
        context: EvaluationContext,
        *,
        rubric_version: str,
        corpus_version: str,
        benchmark_version: str | None = None,
    ) -> FullAnalysisResult:
        """Sync facade for Celery / management commands."""

        return asyncio.run(
            self.evaluate(
                specs,
                context,
                rubric_version=rubric_version,
                corpus_version=corpus_version,
                benchmark_version=benchmark_version,
            )
        )


__all__ = [
    "Band",
    "RubricEvaluationService",
]
