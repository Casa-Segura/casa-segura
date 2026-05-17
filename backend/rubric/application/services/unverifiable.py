"""Unverifiable handling (CS-154).

Translates the heterogeneous "could not verify" outcomes from LLM
evaluation, OCR gaps, F5 absence, and timeout into a single canonical
shape: ``CriterionEvaluation`` rows whose ``score`` equals
``Criterion.worst_case_when_unverifiable`` with an explicit justification
prefix (RUBRICA_CONTRATO §1, PRD_F4 BR-03 / BR-15).

The aggregation in ``score_calculator.aggregate_total`` consumes the
resolved rows directly; this resolver is the only place that overrides
LLM-proposed scores when ``unverifiable=true``.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from rubric.domain.entities import CriterionEvaluation


class UnverifiableReason(StrEnum):
    """Stable codes recorded in the justification of unverifiable rows."""

    MISSING_CLAUSE = "missing_clause"
    OCR_GAP = "ocr_gap"
    F5_BLOCKED = "f5_blocked"
    TIMEOUT = "timeout"
    LLM_FAILURE_AFTER_RETRY = "llm_failure_after_retry"


_JUSTIFICATION_PREFIX = "[unverifiable:{reason}]"


def resolve_unverifiable(
    evaluation: CriterionEvaluation,
    *,
    worst_case_score: float | Decimal,
    reason: UnverifiableReason,
    justification: str | None = None,
) -> CriterionEvaluation:
    """Return a new ``CriterionEvaluation`` with the worst-case score applied.

    Existing fields (``criterion_id``, ``category``, ``weight_in_category``)
    are preserved. The model is immutable except via ``model_copy``; this
    helper centralizes the substitution so a future refactor cannot accidentally
    skip the floor (CS-154 AC: LLM score 10 + unverifiable → still 4).
    """

    if not evaluation.unverifiable:
        raise ValueError(
            f"resolve_unverifiable called on criterion {evaluation.criterion_id} " "whose unverifiable flag is False"
        )
    worst = float(worst_case_score)
    if not 0.0 <= worst <= 10.0:
        raise ValueError(f"worst_case_score {worst} outside [0, 10]")
    justification_text = (justification or evaluation.justification or "").strip()
    prefix = _JUSTIFICATION_PREFIX.format(reason=reason.value)
    if not justification_text.startswith(prefix):
        justification_text = f"{prefix} {justification_text}".strip()
    return evaluation.model_copy(
        update={
            "score": worst,
            "evaluated": False,
            "justification": justification_text,
            # Overrides are never inferred from an unverifiable row — the
            # detection requires positive evidence in the contract.
            "override_triggered": None,
        }
    )


def unverifiable_row(
    *,
    criterion_id: str,
    category: str,
    weight_in_category: float,
    worst_case_score: float | Decimal,
    reason: UnverifiableReason,
    justification: str,
    evidence_snippet: str | None = None,
) -> CriterionEvaluation:
    """Factory for the short-circuit path (CS-154 AC: F5-blocked → no LLM call).

    Used when the pipeline never invokes the LLM at all — for example,
    economic criteria whose ``EconomicSummary`` field is absent (BR-15)
    or when the per-criterion timeout / retry path is exhausted.
    """

    prefix = _JUSTIFICATION_PREFIX.format(reason=reason.value)
    text = justification.strip()
    if not text:
        raise ValueError("justification is required for unverifiable rows (CS-154 BVA)")
    if not text.startswith(prefix):
        text = f"{prefix} {text}"
    worst = float(worst_case_score)
    return CriterionEvaluation(
        criterion_id=criterion_id,
        category=category,  # type: ignore[arg-type]
        applicable=True,
        evaluated=False,
        unverifiable=True,
        score=worst,
        weight_in_category=weight_in_category,
        override_triggered=None,
        justification=text,
        evidence_snippet=evidence_snippet,
    )


def count_unverifiable(evaluations: list[CriterionEvaluation]) -> int:
    """Return the number of unverifiable rows — denormalized for analysis stats."""

    return sum(1 for ev in evaluations if ev.unverifiable)


__all__ = [
    "UnverifiableReason",
    "count_unverifiable",
    "resolve_unverifiable",
    "unverifiable_row",
]
