"""Pydantic schemas for the rubric engine (CS-150).

Mirrors the JSONB shapes persisted in ``ContractAnalysis``
(``scores_by_category``, ``criterion_evaluations``, ``findings``).

Conventions enforced here:

* ``model_config = ConfigDict(extra="forbid")`` — unknown sibling keys
  surface at ingest. CS-150 AC: the policy is explicit and consistent.
* ``CriterionEvaluation.score`` and ``Finding.legal_basis`` cap at
  ``[0, 10]`` and ``len <= 3`` per BR-16 / DOMAIN §3.2.
* ``Finding.evidence_clause_snippet`` and
  ``CriterionEvaluation.evidence_snippet`` accept arbitrary input but
  validators truncate at **500** characters with an ellipsis preserving
  the start of the clause (PRD F4 BR-16).
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.functional_validators import AfterValidator

from rubric.domain.band import Band, OverrideCode, Severity

CategoryLiteral = Literal["A", "B", "C", "D", "E", "F"]

EVIDENCE_SNIPPET_MAX_LEN = 500
LEGAL_BASIS_MAX_ITEMS = 3
_TRUNCATION_SUFFIX = "…"


def _truncate_snippet(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) <= EVIDENCE_SNIPPET_MAX_LEN:
        return value
    return value[: EVIDENCE_SNIPPET_MAX_LEN - 1] + _TRUNCATION_SUFFIX


EvidenceSnippet = Annotated[str | None, AfterValidator(_truncate_snippet)]


class LegalReference(BaseModel):
    """One verbatim citation attached to a Finding (DOMAIN §5.4)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    law_id: str = Field(min_length=1, max_length=64)
    law_title: str = Field(min_length=1, max_length=200)
    article: str = Field(min_length=1, max_length=64)
    anchor: str = Field(min_length=1, max_length=64)
    paraphrased_quote: str = Field(min_length=1, max_length=2000)
    official_source: str | None = Field(default=None, max_length=200)
    corpus_version: str | None = Field(default=None, max_length=32)


class CriterionEvaluation(BaseModel):
    """One row of ``ContractAnalysis.criterion_evaluations`` (DOMAIN §5.2)."""

    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(min_length=1, max_length=8)
    category: CategoryLiteral
    applicable: bool
    evaluated: bool
    unverifiable: bool
    score: float = Field(ge=0.0, le=10.0)
    weight_in_category: float = Field(gt=0.0, le=100.0)
    override_triggered: OverrideCode | None = None
    justification: str = Field(min_length=1, max_length=4000)
    evidence_snippet: EvidenceSnippet = None


class CategoryScore(BaseModel):
    """One row of ``ContractAnalysis.scores_by_category`` (DOMAIN §5.1)."""

    model_config = ConfigDict(extra="forbid")

    category: CategoryLiteral
    category_name: str = Field(min_length=1, max_length=120)
    weight_global: float = Field(ge=0.0, le=1.0)
    weight_effective: float = Field(ge=0.0, le=1.0)
    score: float = Field(ge=0.0, le=10.0)
    criteria_count_total: int = Field(ge=0)
    criteria_count_applicable: int = Field(ge=0)
    criteria_count_unverifiable: int = Field(ge=0)


class Finding(BaseModel):
    """One row of ``ContractAnalysis.findings`` (DOMAIN §5.3)."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=16)
    severity: Severity
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1, max_length=4000)
    evidence_clause_snippet: EvidenceSnippet = None
    legal_basis: list[LegalReference] = Field(default_factory=list)
    recommendation: str = Field(min_length=1, max_length=2000)
    related_criterion_id: str = Field(min_length=1, max_length=8)
    anchors_to_override: OverrideCode | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator("legal_basis")
    @classmethod
    def _cap_legal_basis(cls, value: list[LegalReference]) -> list[LegalReference]:
        if len(value) > LEGAL_BASIS_MAX_ITEMS:
            raise ValueError(f"legal_basis must contain at most {LEGAL_BASIS_MAX_ITEMS} entries")
        return value


class FullAnalysisResult(BaseModel):
    """Output of ``RubricEvaluationService.evaluate`` — persisted in ``ContractAnalysis``."""

    model_config = ConfigDict(extra="forbid")

    score_total: float = Field(ge=0.0, le=10.0)
    band: Band
    override_triggered: list[OverrideCode] = Field(default_factory=list)
    scores_by_category: list[CategoryScore]
    criterion_evaluations: list[CriterionEvaluation]
    findings: list[Finding]
    findings_count: int = Field(ge=0)
    critical_findings_count: int = Field(ge=0)
    unverifiable_count: int = Field(ge=0)
    executive_summary: str = Field(min_length=1, max_length=2000)
    rubric_version: str = Field(min_length=1, max_length=32)
    corpus_version: str = Field(min_length=1, max_length=32)
    benchmark_version: str | None = Field(default=None, max_length=32)


class RawEvaluation(BaseModel):
    """Raw LLM output schema — validated before promotion to ``CriterionEvaluation``."""

    model_config = ConfigDict(extra="ignore")

    criterion_id: str = Field(min_length=1, max_length=8)
    score: float = Field(ge=0.0, le=10.0)
    unverifiable: bool = False
    override_triggered: OverrideCode | None = None
    justification: str = Field(min_length=1, max_length=4000)
    evidence_snippet: EvidenceSnippet = None
    should_emit_finding: bool = True
    finding_severity: Literal["critical", "red", "yellow", "green", "unverifiable"] | None = None
    recommendation: str = Field(min_length=1, max_length=2000)


class RubricSnapshot(BaseModel):
    """Internal bundle assembled before persistence — pre-rendering view of the analysis."""

    model_config = ConfigDict(extra="forbid")

    evaluations: list[CriterionEvaluation]
    category_scores: list[CategoryScore]
    score_total: float
    band: Band
    override_triggered: list[OverrideCode]


__all__ = [
    "EVIDENCE_SNIPPET_MAX_LEN",
    "LEGAL_BASIS_MAX_ITEMS",
    "Band",
    "CategoryLiteral",
    "CategoryScore",
    "CriterionEvaluation",
    "Finding",
    "FullAnalysisResult",
    "LegalReference",
    "OverrideCode",
    "RawEvaluation",
    "RubricSnapshot",
    "Severity",
]
