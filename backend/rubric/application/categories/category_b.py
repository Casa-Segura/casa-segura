"""Category B evaluators — B1..B9 (CS-160).

These evaluators read the deterministic ladders in
``rubric.application.categories.scales`` for the numeric criteria
(B1..B5, B8) and pattern-match the clause-driven criteria (B6, B7,
B9). B7 and B9 wire the ``art_12_lpc`` and ``art_13_lpc`` overrides.

Short-circuit policy (CS-154 / PRD_F4 BR-15): when ``EconomicSummary``
lacks the input a numeric criterion needs, the evaluator returns an
unverifiable row using the catalog's worst-case score — the LLM is
never consulted in that case.
"""

from __future__ import annotations

from decimal import Decimal

from rubric.application.categories import patterns
from rubric.application.categories._helpers import (
    build_evaluation,
    decimal_or_none,
    get_derived,
    get_extracted,
    percent_or_none,
)
from rubric.application.categories.scales import (
    b1_down_payment_score,
    b2_annual_rate_score,
    b3_term_score,
    b4_total_cost_score,
    b5_monthly_ratio_score,
    b8_prepayment_score,
)
from rubric.application.services.criterion_evaluator import (
    CriterionSpec,
    EvaluationContext,
)
from rubric.application.services.unverifiable import (
    UnverifiableReason,
    unverifiable_row,
)
from rubric.domain.band import OverrideCode
from rubric.domain.entities import CriterionEvaluation


def _unverifiable(spec: CriterionSpec, reason: UnverifiableReason, msg: str) -> CriterionEvaluation:
    return unverifiable_row(
        criterion_id=spec.criterion_id,
        category=spec.category,
        weight_in_category=spec.weight_in_category,
        worst_case_score=spec.worst_case_when_unverifiable,
        reason=reason,
        justification=msg,
    )


async def evaluate_b1(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B1 — Reasonable down payment as % of price (§5 B1)."""

    economic = ctx.economic_summary or {}
    pct = percent_or_none(get_extracted(economic, "down_payment_pct"))
    if pct is None:
        return _unverifiable(
            spec,
            UnverifiableReason.F5_BLOCKED,
            "EconomicSummary.down_payment_pct ausente — B1 no verificable (BR-15).",
        )
    ladder = b1_down_payment_score(pct)
    return build_evaluation(
        spec,
        score=ladder.score,
        justification=(
            f"Prima de {pct.normalize()}% del precio total — banda '{ladder.band_label}' "
            "según RUBRICA_CONTRATO §5 B1."
        ),
    )


async def evaluate_b2(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B2 — Effective annual interest rate (§5 B2 + Art. 12 LPC override)."""

    text = ctx.contract_text
    if patterns.find_first(text, patterns.B7_LATE_INTEREST_TOTAL_BALANCE):
        # B7 owns the formal override but Art. 12 LPC also taints B2 — the
        # rubric routes the override through B7; we only adjust B2 score.
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "La cláusula calcula los intereses sobre el saldo total, contradice Art. 12 LPC. "
                "B2 cae a 0 por la base de cálculo."
            ),
        )

    economic = ctx.economic_summary or {}
    annual_rate = decimal_or_none(get_extracted(economic, "annual_rate_pct"))
    if annual_rate is None:
        return _unverifiable(
            spec,
            UnverifiableReason.F5_BLOCKED,
            "Tasa anual ausente y sin equivalente convertible — RUBRICA_CONTRATO §5 B2 unverifiable.",
        )
    # Normalize fraction (0-1) into percent points.
    if annual_rate <= Decimal("1"):
        annual_rate = annual_rate * Decimal("100")
    ladder = b2_annual_rate_score(annual_rate)
    return build_evaluation(
        spec,
        score=ladder.score,
        justification=(
            f"Tasa efectiva anual del {annual_rate.normalize()}% — banda '{ladder.band_label}' "
            "según RUBRICA_CONTRATO §5 B2."
        ),
    )


async def evaluate_b3(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B3 — Credit term (§5 B3)."""

    economic = ctx.economic_summary or {}
    months = decimal_or_none(get_extracted(economic, "term_months"))
    if months is None:
        return _unverifiable(
            spec,
            UnverifiableReason.F5_BLOCKED,
            "Plazo del crédito ausente — B3 no verificable.",
        )
    years = months / Decimal("12")
    ladder = b3_term_score(years)
    return build_evaluation(
        spec,
        score=ladder.score,
        justification=(f"Plazo de {years.normalize()} años — banda '{ladder.band_label}' según §5 B3."),
    )


async def evaluate_b4(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B4 — Computed final total cost (§5 B4)."""

    economic = ctx.economic_summary or {}
    multiplier = decimal_or_none(get_derived(economic, "total_cost_vs_cash_multiplier"))
    if multiplier is None:
        return _unverifiable(
            spec,
            UnverifiableReason.F5_BLOCKED,
            "Multiplicador costo total / precio contado ausente — B4 no verificable.",
        )
    ladder = b4_total_cost_score(multiplier)
    return build_evaluation(
        spec,
        score=ladder.score,
        justification=(
            f"Costo total = {multiplier.normalize()}x del precio contado — "
            f"banda '{ladder.band_label}' según §5 B4."
        ),
    )


async def evaluate_b5(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B5 — Reasonable monthly payment ratio (§5 B5)."""

    economic = ctx.economic_summary or {}
    monthly_payment = decimal_or_none(get_extracted(economic, "monthly_payment"))
    price_cash = decimal_or_none(get_extracted(economic, "price_cash"))
    term_months = decimal_or_none(get_extracted(economic, "term_months"))

    if monthly_payment is None or price_cash is None or term_months is None or term_months <= 0:
        return _unverifiable(
            spec,
            UnverifiableReason.F5_BLOCKED,
            "Faltan plazo o precio para calcular el ratio B5; aplica caso intermedio peor (4).",
        )
    theoretical = price_cash / term_months
    if theoretical <= 0:
        return _unverifiable(
            spec,
            UnverifiableReason.F5_BLOCKED,
            "Cuota teórica no calculable — B5 no verificable.",
        )
    ratio = monthly_payment / theoretical
    ladder = b5_monthly_ratio_score(ratio)
    return build_evaluation(
        spec,
        score=ladder.score,
        justification=(
            f"Ratio B5 = {ratio.normalize()} (cuota mensual / cuota lineal) — " f"banda '{ladder.band_label}'."
        ),
    )


async def evaluate_b6(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B6 — Itemized additional charges (§5 B6).

    Uses elements_detected:
        ``charges_listed_with_amount`` (bool)
        ``charges_open_or_per_policy`` (bool)
    """

    elements = ctx.elements_detected or {}
    if elements.get("charges_open_or_per_policy", False):
        return build_evaluation(spec, score=0.0, justification="Cargos abiertos o 'a criterio del vendedor'.")
    listed = elements.get("charges_listed_with_amount")
    if listed is True:
        return build_evaluation(spec, score=10.0, justification="Cargos itemizados con monto y motivo.")
    if listed is False:
        return build_evaluation(
            spec,
            score=4.0,
            justification="Cargos mencionados pero genéricos ('comisiones administrativas').",
        )
    return build_evaluation(spec, score=7.0, justification="Cargos listados sin desglose explícito por monto.")


async def evaluate_b7(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B7 — Late-payment penalty (§5 B7 + Art. 12 LPC override)."""

    hit = patterns.find_first(ctx.contract_text, patterns.B7_LATE_INTEREST_TOTAL_BALANCE)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Interés moratorio computado sobre saldo total — viola Art. 12 LPC. " "Override forzoso del rubric."
            ),
            evidence_snippet=hit.snippet,
            override_triggered=OverrideCode.ART_12_LPC,
        )
    elements = ctx.elements_detected or {}
    multiplier = elements.get("late_interest_multiplier_over_ordinary")
    if multiplier is None:
        return build_evaluation(
            spec,
            score=7.0,
            justification="Interés moratorio detectado pero sin múltiplo explícito sobre la tasa ordinaria.",
        )
    try:
        mult = Decimal(str(multiplier))
    except Exception:
        mult = Decimal("0")
    if mult <= Decimal("1.5"):
        return build_evaluation(spec, score=10.0, justification="Mora ≤ 1.5x tasa ordinaria sobre capital pendiente.")
    if mult <= Decimal("2"):
        return build_evaluation(spec, score=7.0, justification="Mora ≤ 2x tasa ordinaria sobre capital pendiente.")
    return build_evaluation(spec, score=4.0, justification="Mora > 2x tasa ordinaria sobre capital pendiente.")


async def evaluate_b8(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B8 — Prepayment penalty (§5 B8)."""

    elements = ctx.elements_detected or {}
    if elements.get("prepayment_prohibited", False):
        return build_evaluation(spec, score=0.0, justification="Prepago prohibido o sin justificación.")
    fee_pct = decimal_or_none(elements.get("prepayment_fee_pct"))
    ladder = b8_prepayment_score(fee_pct)
    if fee_pct is None:
        return build_evaluation(
            spec,
            score=ladder.score,
            justification="Sin información clara sobre comisión de prepago.",
        )
    return build_evaluation(
        spec,
        score=ladder.score,
        justification=(f"Comisión de prepago = {fee_pct.normalize()}% — banda '{ladder.band_label}' según §5 B8."),
    )


async def evaluate_b9(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """B9 — Unilateral modification (§5 B9 + Art. 13 LPC override)."""

    hit = patterns.find_first(ctx.contract_text, patterns.B9_UNILATERAL_MODIFICATION)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Permite modificación unilateral de precio o condiciones (Art. 13 LPC). "
                "Override forzoso del rubric."
            ),
            evidence_snippet=hit.snippet,
            override_triggered=OverrideCode.ART_13_LPC,
        )
    elements = ctx.elements_detected or {}
    if elements.get("modification_requires_notice_and_withdrawal", False):
        return build_evaluation(
            spec,
            score=5.0,
            justification="Permite ajustes con preaviso de 30 días y derecho a retiro (§5 B9 banda 5).",
        )
    return build_evaluation(
        spec,
        score=10.0,
        justification="No se permite modificación unilateral del precio o condiciones (§5 B9 banda 10).",
    )


CATEGORY_B_EVALUATORS = {
    "B1": evaluate_b1,
    "B2": evaluate_b2,
    "B3": evaluate_b3,
    "B4": evaluate_b4,
    "B5": evaluate_b5,
    "B6": evaluate_b6,
    "B7": evaluate_b7,
    "B8": evaluate_b8,
    "B9": evaluate_b9,
}


def register_category_b(registry) -> None:
    for criterion_id, fn in CATEGORY_B_EVALUATORS.items():
        registry.register(criterion_id, fn)


__all__ = [
    "CATEGORY_B_EVALUATORS",
    "evaluate_b1",
    "evaluate_b2",
    "evaluate_b3",
    "evaluate_b4",
    "evaluate_b5",
    "evaluate_b6",
    "evaluate_b7",
    "evaluate_b8",
    "evaluate_b9",
    "register_category_b",
]
