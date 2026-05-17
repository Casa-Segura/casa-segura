"""Shared helpers for category evaluators (CS-159..CS-164).

* ``build_evaluation`` — boilerplate-free factory for ``CriterionEvaluation``.
* ``evidence_from`` — sanitize/truncate a candidate snippet to ≤500 chars.
* ``decimal_or_none`` — best-effort coercion for ``EconomicSummary`` values.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from rubric.application.services.criterion_evaluator import CriterionSpec
from rubric.domain.band import OverrideCode
from rubric.domain.entities import CriterionEvaluation


def build_evaluation(
    spec: CriterionSpec,
    *,
    score: float,
    justification: str,
    evidence_snippet: str | None = None,
    override_triggered: OverrideCode | None = None,
    unverifiable: bool = False,
    applicable: bool = True,
) -> CriterionEvaluation:
    """Construct a ``CriterionEvaluation`` from a ``CriterionSpec``.

    Centralizes the constant fields (``criterion_id``, ``category``,
    ``weight_in_category``) so each evaluator focuses on the variant.
    """

    return CriterionEvaluation(
        criterion_id=spec.criterion_id,
        category=spec.category,  # type: ignore[arg-type]
        applicable=applicable,
        evaluated=not unverifiable,
        unverifiable=unverifiable,
        score=score,
        weight_in_category=spec.weight_in_category,
        override_triggered=override_triggered,
        justification=justification.strip(),
        evidence_snippet=evidence_snippet,
    )


def decimal_or_none(value: Any) -> Decimal | None:
    """Best-effort Decimal coercion that accepts EconomicSummary serializations."""

    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError):
            return None
    return None


def percent_or_none(value: Any) -> Decimal | None:
    """Coerce a value to a *percentage* Decimal (e.g. 10 means 10 %).

    EconomicSummary stores ``down_payment_pct`` as a fraction (0-1) per
    F5; this helper accepts both fractions and percent-points and
    normalizes to percent-points so the rubric ladders read naturally.
    """

    dec = decimal_or_none(value)
    if dec is None:
        return None
    if dec <= Decimal("1") and dec >= Decimal("0"):
        return dec * Decimal("100")
    return dec


def get_extracted(context_dict: dict[str, Any], key: str) -> Any:
    """Read a value from the ``fields_extracted`` nested block."""

    fields = context_dict.get("fields_extracted") or {}
    return fields.get(key)


def get_derived(context_dict: dict[str, Any], key: str) -> Any:
    fields = context_dict.get("fields_derived") or {}
    return fields.get(key)


__all__ = [
    "build_evaluation",
    "decimal_or_none",
    "get_derived",
    "get_extracted",
    "percent_or_none",
]
