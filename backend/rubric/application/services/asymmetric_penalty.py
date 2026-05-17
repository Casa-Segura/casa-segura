"""Asymmetric-penalty clamp (CS-153).

Rubric §1.1 is explicit: conditions **favorable** to the buyer or
tenant against the market average never reduce the score. The LLM may
return a lower score when, say, the down payment is 3 % (below the 10 %
benchmark) — this clamp rescues the rubric-prescribed ordering by
pinning the score to *at least* the benchmark-tier value.

The clamp is one-sided. Values *worse* than the benchmark stay where
the evaluator put them — this is the asymmetric guarantee.

Each policy is keyed by the criterion code; the data it consumes lives
in ``EconomicSummary`` (PRD_F5 §5) and ``RUBRICA_CONTRATO`` §5 scales.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from rubric.domain.entities import CriterionEvaluation

logger = logging.getLogger(__name__)


class MetricDirection(StrEnum):
    """Direction along which "better" is defined for a criterion."""

    LOWER_IS_BETTER = "lower_is_better"  # B1 down payment, B2 rate, B4 total cost
    HIGHER_IS_BETTER = "higher_is_better"  # B3 short term still scores 10 per rubric
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class AsymmetricInputs:
    """Inputs the clamp needs from F5 (already typed into ``EconomicSummary``)."""

    contract_value: Decimal | None
    benchmark_reference: Decimal | None
    direction: MetricDirection = MetricDirection.LOWER_IS_BETTER


@dataclass(frozen=True)
class ClampOutcome:
    score: float
    applied: bool
    reason: str  # e.g. "lifted_to_benchmark_tier" / "skipped_missing_benchmark"


# Per-criterion benchmark-tier scores (the top score the rubric awards
# when the contract value equals the benchmark). Sourced from
# RUBRICA_CONTRATO §5 scales: B1 favorable ≤ 10 %, B2 favorable ≤ 9 %,
# B4 favorable ≤ 1.5x.
_BENCHMARK_TIER_SCORE: dict[str, Decimal] = {
    "B1": Decimal("10"),
    "B2": Decimal("10"),
    "B3": Decimal("10"),
    "B4": Decimal("10"),
}


def _favorable(contract: Decimal, benchmark: Decimal, direction: MetricDirection) -> bool:
    if direction == MetricDirection.LOWER_IS_BETTER:
        return contract <= benchmark
    if direction == MetricDirection.HIGHER_IS_BETTER:
        return contract >= benchmark
    return False


def clamp_score(
    *,
    criterion_id: str,
    raw_score: float | Decimal,
    inputs: AsymmetricInputs,
) -> ClampOutcome:
    """Apply CS-153 asymmetric clamp to a per-criterion score.

    Returns the original score unchanged unless the contract value is
    *more favorable* than the benchmark and the LLM proposed a score
    below the benchmark-tier ceiling. In that case the score is lifted
    to the tier ceiling (typically 10).
    """

    raw = Decimal(str(raw_score))
    if inputs.contract_value is None or inputs.benchmark_reference is None:
        logger.info(
            "rubric.asymmetric.skipped",
            extra={"criterion_id": criterion_id, "reason": "ASYMMETRIC_SKIPPED_REASON"},
        )
        return ClampOutcome(score=float(raw), applied=False, reason="ASYMMETRIC_SKIPPED_REASON")

    if not _favorable(inputs.contract_value, inputs.benchmark_reference, inputs.direction):
        return ClampOutcome(score=float(raw), applied=False, reason="not_favorable")

    ceiling = _BENCHMARK_TIER_SCORE.get(criterion_id, Decimal("10"))
    if raw >= ceiling:
        return ClampOutcome(score=float(raw), applied=False, reason="already_at_or_above_ceiling")
    return ClampOutcome(
        score=float(ceiling),
        applied=True,
        reason="lifted_to_benchmark_tier",
    )


def apply_clamp_to_evaluation(
    evaluation: CriterionEvaluation,
    *,
    inputs: AsymmetricInputs,
) -> CriterionEvaluation:
    """Return a new evaluation with the clamped score (justification untouched)."""

    outcome = clamp_score(
        criterion_id=evaluation.criterion_id,
        raw_score=evaluation.score,
        inputs=inputs,
    )
    if not outcome.applied:
        return evaluation
    return evaluation.model_copy(update={"score": outcome.score})


# ── Convenience constructors per criterion ──────────────────────────────

InputBuilder = Callable[..., AsymmetricInputs]


def b1_inputs(
    *,
    contract_down_payment_pct: Decimal | None,
    benchmark_down_payment_pct: Decimal | None,
) -> AsymmetricInputs:
    return AsymmetricInputs(
        contract_value=contract_down_payment_pct,
        benchmark_reference=benchmark_down_payment_pct,
        direction=MetricDirection.LOWER_IS_BETTER,
    )


def b2_inputs(
    *,
    contract_annual_rate_pct: Decimal | None,
    benchmark_segment_mid_pct: Decimal | None,
) -> AsymmetricInputs:
    return AsymmetricInputs(
        contract_value=contract_annual_rate_pct,
        benchmark_reference=benchmark_segment_mid_pct,
        direction=MetricDirection.LOWER_IS_BETTER,
    )


def b3_inputs(
    *,
    contract_term_months: Decimal | None,
    benchmark_reasonable_max_months: Decimal | None,
) -> AsymmetricInputs:
    # B3 rewards shorter terms (consistent with the rubric's stance on
    # avoiding pathologically long financings); "lower is better".
    return AsymmetricInputs(
        contract_value=contract_term_months,
        benchmark_reference=benchmark_reasonable_max_months,
        direction=MetricDirection.LOWER_IS_BETTER,
    )


def b4_inputs(
    *,
    contract_total_cost_multiplier: Decimal | None,
    benchmark_healthy_max_multiplier: Decimal | None,
) -> AsymmetricInputs:
    return AsymmetricInputs(
        contract_value=contract_total_cost_multiplier,
        benchmark_reference=benchmark_healthy_max_multiplier,
        direction=MetricDirection.LOWER_IS_BETTER,
    )


__all__ = [
    "AsymmetricInputs",
    "ClampOutcome",
    "MetricDirection",
    "apply_clamp_to_evaluation",
    "b1_inputs",
    "b2_inputs",
    "b3_inputs",
    "b4_inputs",
    "clamp_score",
]
