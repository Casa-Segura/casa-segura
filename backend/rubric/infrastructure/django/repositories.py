"""Repositories that bridge the rubric application layer to Django ORM.

* ``CriterionRepository`` — loads ``Criterion`` rows either for the stamped
  ``ContractAnalysis.rubric_version`` or, when bootstrap applies, for the active
  ``RubricVersion`` (see ``load_specs_for_analysis`` / CS-358).
* ``ContractAnalysisRepository`` — writes the ``FullAnalysisResult`` back
  onto the ``ContractAnalysis`` row (PRD_F4 US-07). The write is atomic:
  every column the rubric owns is updated in one ``save()`` call.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from platform_core.infrastructure.django.models import ContractAnalysis
from rubric.application.services.criterion_evaluator import CriterionSpec
from rubric.domain.entities import FullAnalysisResult
from rubric.infrastructure.django.models import Criterion, RubricVersion

# Log / analytics: where rubric criterion rows came from for a scoring run.
RUBRIC_CATALOG_STAMPED = "stamped"
RUBRIC_CATALOG_ACTIVE_BOOTSTRAP = "active_bootstrap"


class CriterionRepository:
    """Read-only lookup over the rubric catalog."""

    def load_active_specs(self) -> tuple[list[CriterionSpec], str]:
        """Return all ``CriterionSpec`` rows + the active rubric version string."""

        active = RubricVersion.objects.filter(is_active=True).first()
        if active is None:
            raise LookupError("RUBRIC_VERSION_NOT_ACTIVE: no active rubric version configured")
        return self.load_specs_for_version(active.version), active.version

    def load_specs_for_version(self, version: str) -> list[CriterionSpec]:
        rows = Criterion.objects.filter(rubric_version_id=version).order_by("code")
        return [
            CriterionSpec(
                criterion_id=row.code,
                category=row.category,
                weight_in_category=float(row.weight_in_category),
                applicable_types=tuple(row.applicable_types or ()),
                legal_anchor=tuple(row.legal_anchor or ()),
                override_code=row.override_code,
                evaluation_prompt=row.evaluation_prompt,
                scoring_scale=row.scoring_scale or {},
                worst_case_when_unverifiable=float(row.worst_case_when_unverifiable),
            )
            for row in rows
        ]

    def load_specs_for_analysis(
        self,
        analysis: ContractAnalysis,
    ) -> tuple[list[CriterionSpec], str, str]:
        """Resolve specs for scoring: stamped `ContractAnalysis` rubric, else active catalog.

        Returns ``(specs, resolved_rubric_version_string, rubric_catalog_source)`` where
        ``rubric_catalog_source`` is ``RUBRIC_CATALOG_STAMPED`` or
        ``RUBRIC_CATALOG_ACTIVE_BOOTSTRAP`` (defensive: unsaved rows / future stubs).
        """

        stamp = getattr(analysis, "rubric_version_id", None)
        if stamp:
            return (
                self.load_specs_for_version(stamp),
                stamp,
                RUBRIC_CATALOG_STAMPED,
            )
        specs, active_version = self.load_active_specs()
        return specs, active_version, RUBRIC_CATALOG_ACTIVE_BOOTSTRAP


class ContractAnalysisRepository:
    """Persists the rubric output onto an existing ``ContractAnalysis`` row."""

    @transaction.atomic
    def persist(self, analysis_id: str, result: FullAnalysisResult) -> ContractAnalysis:
        """Write every rubric-owned column in one transaction (PRD_F4 US-07).

        ``ContractAnalysis`` rows are created at submission time with the
        scoring columns NULL; this method fills them once the engine
        completes. The whole payload — categories, evaluations, findings,
        executive summary, version stamps — lands together so callers
        observe an "all or nothing" snapshot.
        """

        analysis = ContractAnalysis.objects.select_for_update().get(pk=analysis_id)
        analysis.score_total = Decimal(str(result.score_total))
        analysis.band = result.band.value
        analysis.override_triggered = [code.value for code in result.override_triggered]
        analysis.scores_by_category = [cs.model_dump() for cs in result.scores_by_category]
        analysis.criterion_evaluations = [self._dump_evaluation(ev) for ev in result.criterion_evaluations]
        analysis.findings = [self._dump_finding(f) for f in result.findings]
        analysis.findings_count = result.findings_count
        analysis.critical_findings_count = result.critical_findings_count
        analysis.unverifiable_count = result.unverifiable_count
        analysis.executive_summary = result.executive_summary
        analysis.rubric_version_id = result.rubric_version
        analysis.corpus_version_id = result.corpus_version
        if result.benchmark_version is not None:
            analysis.benchmark_version_id = result.benchmark_version

        analysis.save(
            update_fields=[
                "score_total",
                "band",
                "override_triggered",
                "scores_by_category",
                "criterion_evaluations",
                "findings",
                "findings_count",
                "critical_findings_count",
                "unverifiable_count",
                "executive_summary",
                "rubric_version",
                "corpus_version",
                "benchmark_version",
                "updated_at",
            ]
        )
        return analysis

    def _dump_evaluation(self, ev) -> dict:
        payload = ev.model_dump()
        # Serialize OverrideCode enum to its string value.
        if payload.get("override_triggered") is not None:
            payload["override_triggered"] = ev.override_triggered.value
        return payload

    def _dump_finding(self, f) -> dict:
        payload = f.model_dump()
        if payload.get("anchors_to_override") is not None:
            payload["anchors_to_override"] = f.anchors_to_override.value
        payload["severity"] = f.severity.value
        payload["legal_basis"] = [ref.model_dump() for ref in f.legal_basis]
        return payload


__all__ = [
    "RUBRIC_CATALOG_ACTIVE_BOOTSTRAP",
    "RUBRIC_CATALOG_STAMPED",
    "ContractAnalysisRepository",
    "CriterionRepository",
]
