"""Leasing reclassification result envelope (CS-111).

The detector defined in ``classification.application.leasing_detector``
returns one of these per CS-110 output. The orchestrator (CS-112+)
decides whether to **apply** the recommendation; this DTO is purely a
recommendation envelope and never mutates the upstream
:class:`~classification.domain.dtos.ClassificationResult`.

Semantics
---------
- ``original_type`` — the type CS-110 produced for this submission.
- ``recommended_type`` — either ``LEA`` (when the detector recommends
  reclassification) or ``original_type`` (when it does not / when the
  detector was skipped because the original type is not in the
  applicable set ``{CVC, CVP, APV}``, PRD F2 BR-02).
- ``should_reclassify`` — ``True`` iff ``recommended_type != original_type``.
  Kept as a denormalized boolean so consumers do not have to compare
  enum values; a validator enforces it stays consistent.
- ``indicators`` — the six Art. 2 LAF flags the detector extracted
  (all ``False`` on the skip path).
- ``confidence`` — model self-reported confidence in the indicator set
  (``0.0`` on the skip path).
- ``reasoning`` — short Spanish justification surfaced for QA/logging
  only. MUST NOT contain raw clauses with PII (BR-07).
- ``severity`` — discrete bucket the orchestrator persists on
  ``ContractAnalysis.reclassification_indicators`` (PRD §8.4 warning
  artifact for the 2-3 indicators band). Computed from the indicator
  count; see :class:`LeasingSeverity`.

DDD note
--------
Domain layer; pydantic v2 only. No Django / HTTP / LLM client imports.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from classification.domain.contract_type import ContractType
from classification.domain.leasing_indicators import (
    DEFAULT_RECLASSIFICATION_THRESHOLD,
    LeasingIndicators,
)


class LeasingSeverity(StrEnum):
    """Discrete severity bucket for the §8.4 warning artifact (PRD F2 §8.4).

    Mapping (single source of truth — see :func:`severity_from_count`):

        count ∈ {0, 1}  → NONE    (no warning, silent path per US-03)
        count == 2      → LOW     (early signal; orchestrator emits warning)
        count == 3      → MEDIUM  (yellow finding for EPIC-06)
        count ≥ 4       → HIGH    (full reclassification to LEA — BR-03)

    The mapping mirrors PRD F2 §8.4's wording: 2 indicators is "low-severity
    suspicion", 3 is "medium-severity warning", 4+ is the reclassification
    threshold. Keep this aligned with ``DEFAULT_RECLASSIFICATION_THRESHOLD``
    in ``leasing_indicators``: changing the legal-product hinge (BR-03)
    requires updating BOTH the threshold and the severity boundary.
    """

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def severity_from_count(count: int) -> LeasingSeverity:
    """Map an Art. 2 LAF indicator count onto a :class:`LeasingSeverity`.

    Exposed as a free function so callers (orchestrator, tests, future
    eval harness) reuse one comparison. Negative or out-of-range counts
    raise ``ValueError`` — the detector enforces ``0 ≤ count ≤ 6`` via
    ``LeasingIndicators``; an out-of-range value here means caller bug.
    """
    if count < 0:
        raise ValueError(f"indicator count must be >= 0; got {count!r}")
    if count >= DEFAULT_RECLASSIFICATION_THRESHOLD:
        return LeasingSeverity.HIGH
    if count == 3:
        return LeasingSeverity.MEDIUM
    if count == 2:
        return LeasingSeverity.LOW
    return LeasingSeverity.NONE


class LeasingReclassificationResult(BaseModel):
    """Recommendation envelope produced by ``LeasingReclassificationDetector``.

    Frozen + ``extra="forbid"`` to match the rest of the domain layer:
    callers may not stash side-channel data on this object, and the
    orchestrator can treat it as a value type.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    original_type: ContractType = Field(
        description="The ContractType CS-110 produced for this submission.",
    )
    recommended_type: ContractType = Field(
        description=(
            "Either LEA (reclassify) or original_type (keep). The "
            "orchestrator decides whether to apply this recommendation."
        ),
    )
    should_reclassify: bool = Field(
        description=(
            "Denormalized flag: True iff recommended_type != original_type. " "Enforced by a model validator."
        ),
    )
    indicators: LeasingIndicators = Field(
        description=(
            "The six Art. 2 LAF flags the detector extracted. All False "
            "on the skip path (original_type not in {CVC, CVP, APV})."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Model self-reported confidence in the indicator set. 0.0 on "
            "the skip path. Downstream banding lives in CS-112+."
        ),
    )
    reasoning: str | None = Field(
        default=None,
        max_length=1000,
        description=(
            "Short Spanish justification for QA/logging only. MUST NOT "
            "include real names, addresses, DUI, IBAN, phones, or emails."
        ),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def severity(self) -> LeasingSeverity:
        """Discrete severity bucket derived from the indicator count.

        Drives the JSONB shape the orchestrator (CS-112+) writes to
        ``ContractAnalysis.reclassification_indicators``:

            {"indicators": {...six bools...}, "count": N, "severity": "..."}

        See :func:`severity_from_count` for the mapping. Exposed as a
        computed property so callers cannot drift away from
        ``LeasingIndicators.total_indicators_found``.
        """
        return severity_from_count(self.indicators.total_indicators_found)

    @model_validator(mode="after")
    def _check_reclassify_consistency(self) -> LeasingReclassificationResult:
        # Keep should_reclassify and recommended_type in lockstep so
        # consumers can trust either field. Enforced after construction
        # because both fields are required at the same time.
        derived = self.recommended_type != self.original_type
        if self.should_reclassify != derived:
            raise ValueError(
                "should_reclassify must equal (recommended_type != original_type); "
                f"got should_reclassify={self.should_reclassify!r}, "
                f"original={self.original_type.value}, "
                f"recommended={self.recommended_type.value}"
            )
        # A reclassification can only ever recommend LEA (PRD US-03).
        if self.should_reclassify and self.recommended_type is not ContractType.LEA:
            raise ValueError(
                "recommended_type must be LEA when should_reclassify is True; " f"got {self.recommended_type.value}"
            )
        return self


__all__ = ["LeasingReclassificationResult", "LeasingSeverity", "severity_from_count"]
