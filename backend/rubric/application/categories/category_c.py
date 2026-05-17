"""Category C evaluators — C1..C7 (CS-161).

Guarantees for buyer/tenant per RUBRICA_CONTRATO §6. C5 emits the
``art_1644_cc`` override on a bad-faith eviction-warranty waiver.
"""

from __future__ import annotations

from rubric.application.categories import patterns
from rubric.application.categories._helpers import build_evaluation
from rubric.application.services.criterion_evaluator import (
    CriterionSpec,
    EvaluationContext,
)
from rubric.domain.band import OverrideCode
from rubric.domain.entities import CriterionEvaluation


async def evaluate_c1(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """C1 — Escrow or trust mechanism for down payment (§6 C1)."""

    elements = ctx.elements_detected or {}
    mechanism = elements.get("down_payment_mechanism")
    score_map = {
        "escrow": (10.0, "Prima depositada en escrow bancario o cuenta conjunta (§6 C1 banda 10)."),
        "notarial_receipt": (
            7.0,
            "Prima en cuenta del vendedor pero con recibo notarial y comprobante de destino.",
        ),
        "simple_receipt": (4.0, "Prima entregada con simple recibo (§6 C1 banda 4)."),
        "cash_unprotected": (0.0, "Prima entregada en efectivo sin protección ni reembolso."),
    }
    if mechanism in score_map:
        score, justification = score_map[mechanism]
        return build_evaluation(spec, score=score, justification=justification)
    return build_evaluation(spec, score=4.0, justification="Mecanismo de garantía sobre la prima no claro (§6 C1).")


async def evaluate_c2(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """C2 — Certain delivery date (§6 C2)."""

    elements = ctx.elements_detected or {}
    mode = elements.get("delivery_date_mode")
    table = {
        "exact_date_with_penalty": (10.0, "Fecha exacta de entrega con penalidad cuantificada."),
        "month_year_with_penalty": (7.0, "Rango (mes y año) con penalidad."),
        "approximate_months": (4.0, "'Aproximadamente N meses' con penalidad genérica (§6 C2 banda 4)."),
        "open_ended": (0.0, "'Cuando se termine la construcción' sin penalidad — peor caso §6 C2."),
    }
    if mode in table:
        score, justification = table[mode]
        return build_evaluation(spec, score=score, justification=justification)
    return build_evaluation(spec, score=4.0, justification="Fecha de entrega ambigua o no especificada.")


async def evaluate_c3(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """C3 — Penalty for seller/lessor delay (§6 C3)."""

    elements = ctx.elements_detected or {}
    posture = elements.get("seller_delay_penalty")
    table = {
        "symmetric_or_higher": (10.0, "Penalidad simétrica o mayor a la del comprador en mora."),
        "lower_than_symmetric": (6.0, "Penalidad presente pero menor a la simétrica del comprador."),
        "symbolic": (3.0, "Penalidad simbólica o menor al interés legal mercantil."),
        "absent_or_excluded": (
            0.0,
            "Sin penalidad o cláusula que exime al vendedor por mora — incumple Art. 1714 CC.",
        ),
    }
    if posture in table:
        score, justification = table[posture]
        return build_evaluation(spec, score=score, justification=justification)
    return build_evaluation(
        spec, score=4.0, justification="Penalidad por mora del vendedor/arrendador no especificada."
    )


async def evaluate_c4(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """C4 — Treatment of seller non-compliance (§6 C4)."""

    elements = ctx.elements_detected or {}
    posture = elements.get("seller_breach_clause")
    table = {
        "full_refund_with_interest": (10.0, "Devolución total + interés legal mercantil ante incumplimiento."),
        "refund_minus_5_pct": (7.0, "Devolución con retención menor al 5% (§6 C4 banda 7)."),
        "partial_or_onerous": (4.0, "Devolución parcial o sujeta a condiciones onerosas."),
        "no_refund": (
            0.0,
            "Pagos a cuenta no reembolsables ante incumplimiento del vendedor — infracción grave Art. 43 lit. d LPC.",
        ),
    }
    if posture in table:
        score, justification = table[posture]
        return build_evaluation(spec, score=score, justification=justification)
    return build_evaluation(spec, score=4.0, justification="Política de incumplimiento del vendedor no clara.")


async def evaluate_c5(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """C5 — Warranty against eviction & hidden defects (§6 C5 + Art. 1644 CC)."""

    hit = patterns.find_first(ctx.contract_text, patterns.C5_WARRANTY_WAIVER)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Cláusula que exime del saneamiento por evicción — Art. 1644 CC declara nulo "
                "el pacto cuando el vendedor obra de mala fe."
            ),
            evidence_snippet=hit.snippet,
            override_triggered=OverrideCode.ART_1644_CC,
        )
    elements = ctx.elements_detected or {}
    posture = elements.get("warranty_clause")
    if posture == "explicit_full_coverage":
        return build_evaluation(spec, score=10.0, justification="Cláusula expresa de saneamiento con plazo ≥ 1 año.")
    if posture == "limited":
        return build_evaluation(
            spec, score=7.0, justification="Saneamiento mencionado pero limitado a aspectos específicos."
        )
    if posture == "silent":
        return build_evaluation(
            spec,
            score=4.0,
            justification="Silencio total — el Código Civil aplica supletoriamente (§6 C5 banda 4).",
        )
    return build_evaluation(spec, score=4.0, justification="Saneamiento no detectado con claridad — caso intermedio.")


async def evaluate_c6(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """C6 — Right to a receipt for each payment (§6 C6)."""

    elements = ctx.elements_detected or {}
    receipt = elements.get("receipt_obligation")
    if receipt == "explicit":
        return build_evaluation(spec, score=10.0, justification="Obligación de emitir recibo expresada en contrato.")
    if receipt == "implicit":
        return build_evaluation(
            spec, score=6.0, justification="Recibo implícito; aplica supletoriamente Ley de Inquilinato."
        )
    if receipt == "exempted":
        return build_evaluation(
            spec,
            score=0.0,
            justification="Cláusula que exime de emitir recibo — nula (Art. 9 Ley de Inquilinato).",
        )
    return build_evaluation(spec, score=6.0, justification="Sin mención explícita — se asume Ley supletoria.")


async def evaluate_c7(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """C7 — Contract continuity on death or transfer (§6 C7)."""

    elements = ctx.elements_detected or {}
    posture = elements.get("continuity_clause")
    if posture == "extinguishes_on_death":
        return build_evaluation(
            spec,
            score=0.0,
            justification="Cláusula que extingue el contrato por muerte del arrendatario — contraria a Arts. 27/28 Ley de Inquilinato.",
        )
    return build_evaluation(
        spec,
        score=10.0,
        justification="Continuidad reconocida o silencio (aplica supletoriamente Ley de Inquilinato).",
    )


CATEGORY_C_EVALUATORS = {
    "C1": evaluate_c1,
    "C2": evaluate_c2,
    "C3": evaluate_c3,
    "C4": evaluate_c4,
    "C5": evaluate_c5,
    "C6": evaluate_c6,
    "C7": evaluate_c7,
}


def register_category_c(registry) -> None:
    for criterion_id, fn in CATEGORY_C_EVALUATORS.items():
        registry.register(criterion_id, fn)


__all__ = [
    "CATEGORY_C_EVALUATORS",
    "evaluate_c1",
    "evaluate_c2",
    "evaluate_c3",
    "evaluate_c4",
    "evaluate_c5",
    "evaluate_c6",
    "evaluate_c7",
    "register_category_c",
]
