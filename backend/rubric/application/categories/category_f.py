"""Category F evaluators — F1..F5 (CS-164).

Transparency criteria + post-evaluation hook to enrich findings with
F3 (corpus) legal citations. See ``finding_factory.py`` for the
citation pass; this module only owns the scoring ladders.
"""

from __future__ import annotations

from rubric.application.categories import patterns
from rubric.application.categories._helpers import (
    build_evaluation,
    decimal_or_none,
    get_extracted,
)
from rubric.application.services.criterion_evaluator import (
    CriterionSpec,
    EvaluationContext,
)
from rubric.domain.entities import CriterionEvaluation


async def evaluate_f1(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """F1 — Spanish language and legible characters (§9 F1)."""

    text = ctx.contract_text
    elements = ctx.elements_detected or {}
    if elements.get("illegible_or_microfont", False):
        return build_evaluation(spec, score=0.0, justification="Caracteres ilegibles o fuente microscópica detectada.")
    if patterns.find_first(text, patterns.F1_FOREIGN_LANGUAGE):
        if elements.get("dominant_language", "es") != "es":
            return build_evaluation(
                spec,
                score=0.0,
                justification="Idioma dominante distinto del español — incumple Art. 22 LPC.",
            )
        return build_evaluation(
            spec,
            score=6.0,
            justification="Fragmento en otro idioma o terminología excesivamente técnica detectado.",
        )
    return build_evaluation(spec, score=10.0, justification="Español claro y tipografía legible.")


async def evaluate_f2(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """F2 — Referenced exhibits actually attached (§9 F2)."""

    elements = ctx.elements_detected or {}
    posture = elements.get("exhibits_status")
    table = {
        "all_attached": (10.0, "Todos los anexos referenciados están adjuntos."),
        "non_critical_missing": (6.0, "Algunos anexos faltan pero no son críticos (§9 F2 banda 6)."),
        "critical_missing": (0.0, "Faltan anexos críticos (planos, especificaciones, garantías)."),
    }
    if posture in table:
        score, justification = table[posture]
        return build_evaluation(spec, score=score, justification=justification)
    return build_evaluation(
        spec, score=6.0, justification="Anexos referenciados sin confirmar adjuntos explícitamente."
    )


async def evaluate_f3(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """F3 (rubric) — Right of withdrawal (§9 F3)."""

    hit = patterns.find_first(ctx.contract_text, patterns.F3_WITHDRAWAL_RIGHT)
    if hit is not None:
        return build_evaluation(
            spec, score=10.0, justification="Derecho de retracto comunicado claramente.", evidence_snippet=hit.snippet
        )
    elements = ctx.elements_detected or {}
    posture = elements.get("withdrawal_right_disclosure")
    if posture == "partial":
        return build_evaluation(
            spec, score=5.0, justification="Mención parcial del derecho de retracto (§9 F3 banda 5)."
        )
    if posture == "denied":
        return build_evaluation(spec, score=0.0, justification="Cláusula que niega o penaliza el derecho de retracto.")
    return build_evaluation(
        spec,
        score=0.0,
        justification="No se comunica el derecho de retracto (§9 F3 banda 0).",
    )


async def evaluate_f4(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """F4 (rubric) — Total cost stated (§9 F4)."""

    hit = patterns.find_first(ctx.contract_text, patterns.F4_TOTAL_COST_STATED)
    economic = ctx.economic_summary or {}
    total_cost = decimal_or_none((economic.get("fields_derived") or {}).get("total_cost_paid"))
    if hit is not None:
        return build_evaluation(
            spec,
            score=10.0,
            justification="Costo total expresado y comparable con el precio contado.",
            evidence_snippet=hit.snippet,
        )
    if total_cost is not None:
        return build_evaluation(
            spec, score=5.0, justification="Costo total deducible pero no expresado explícitamente."
        )
    return build_evaluation(spec, score=0.0, justification="Costo total no expresado y difícil de calcular.")


async def evaluate_f5(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """F5 (rubric) — Effective annual rate stated (§9 F5)."""

    hit = patterns.find_first(ctx.contract_text, patterns.F5_EAR_STATED)
    economic = ctx.economic_summary or {}
    monthly_rate = decimal_or_none(get_extracted(economic, "monthly_rate_pct"))
    annual_rate = decimal_or_none(get_extracted(economic, "annual_rate_pct"))
    if hit is not None or annual_rate is not None:
        return build_evaluation(
            spec,
            score=10.0,
            justification="Tasa expresada como anual efectiva, en porcentaje.",
            evidence_snippet=hit.snippet if hit else None,
        )
    if monthly_rate is not None:
        return build_evaluation(
            spec,
            score=5.0,
            justification="Tasa mensual expresada pero no convertida a anual efectiva.",
        )
    return build_evaluation(spec, score=0.0, justification="Tasa de interés no expresada.")


CATEGORY_F_EVALUATORS = {
    "F1": evaluate_f1,
    "F2": evaluate_f2,
    "F3": evaluate_f3,
    "F4": evaluate_f4,
    "F5": evaluate_f5,
}


def register_category_f(registry) -> None:
    for criterion_id, fn in CATEGORY_F_EVALUATORS.items():
        registry.register(criterion_id, fn)


__all__ = [
    "CATEGORY_F_EVALUATORS",
    "evaluate_f1",
    "evaluate_f2",
    "evaluate_f3",
    "evaluate_f4",
    "evaluate_f5",
    "register_category_f",
]
