"""Category E evaluators — E1..E9 (CS-163).

Abusive clauses per RUBRICA_CONTRATO §8. Mostly binary (10 vs 0). E1
emits ``art_5_lpc_non_waivable``, E6 emits ``art_18_lpc_blank_signature``,
E7 emits ``art_17h_lpc_arbitration``. E9 allows intermediate score 5
for the justified-high-penalty edge.
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


async def evaluate_e1(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E1 — Waiver of non-waivable rights (Art. 5 LPC override)."""

    hit = patterns.find_first(ctx.contract_text, patterns.E1_RIGHT_WAIVER)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=("Cláusula que renuncia a derechos legales del consumidor — Art. 5 LPC declara nula."),
            evidence_snippet=hit.snippet,
            override_triggered=OverrideCode.ART_5_LPC_NON_WAIVABLE,
        )
    return build_evaluation(spec, score=10.0, justification="No se detecta renuncia a derechos del consumidor.")


async def evaluate_e2(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E2 — Warranty waiver (§8 E2)."""

    hit = patterns.find_first(ctx.contract_text, patterns.E2_WARRANTY_EXEMPTION)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification="Cláusula de exoneración del saneamiento detectada.",
            evidence_snippet=hit.snippet,
        )
    return build_evaluation(spec, score=10.0, justification="Sin cláusula de exoneración del saneamiento.")


async def evaluate_e3(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E3 — Burden-of-proof reversal (§8 E3)."""

    hit = patterns.find_first(ctx.contract_text, patterns.E3_BURDEN_REVERSAL)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification="Cláusula que invierte la carga de la prueba — abusiva (Art. 17 LPC).",
            evidence_snippet=hit.snippet,
        )
    return build_evaluation(spec, score=10.0, justification="No se detecta inversión de la carga de la prueba.")


async def evaluate_e4(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E4 — Automatic renewal without consent (§8 E4)."""

    hit = patterns.find_first(ctx.contract_text, patterns.E4_AUTO_RENEWAL)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification="Cláusula de renovación automática sin consentimiento expreso.",
            evidence_snippet=hit.snippet,
        )
    return build_evaluation(
        spec, score=10.0, justification="Sin renovación automática que prescinda del consentimiento."
    )


async def evaluate_e5(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E5 — Notary imposed by provider (§8 E5)."""

    hit = patterns.find_first(ctx.contract_text, patterns.E5_NOTARY_IMPOSED)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification="El vendedor impone notario — infracción Art. 19/20/44 LPC.",
            evidence_snippet=hit.snippet,
        )
    return build_evaluation(spec, score=10.0, justification="El comprador elige notario o el contrato no impone.")


async def evaluate_e6(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E6 — Blank signature on obligation documents (Art. 18 lit. b LPC override)."""

    hit = patterns.find_first(ctx.contract_text, patterns.E6_BLANK_SIGNATURE)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Requerimiento de firmar pagarés, letras u otros documentos en blanco — "
                "Art. 18 lit. b LPC prohibe esta práctica."
            ),
            evidence_snippet=hit.snippet,
            override_triggered=OverrideCode.ART_18_LPC_BLANK_SIGNATURE,
        )
    return build_evaluation(spec, score=10.0, justification="No requiere firmar documentos en blanco.")


async def evaluate_e7(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E7 — Arbitration imposed in adhesion contract (Art. 17 lit. h LPC override)."""

    hit = patterns.find_first(ctx.contract_text, patterns.E7_ARBITRATION)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=("Cláusula de arbitraje impuesta en contrato de adhesión — Art. 17 lit. h / 44 lit. g LPC."),
            evidence_snippet=hit.snippet,
            override_triggered=OverrideCode.ART_17H_LPC_ARBITRATION,
        )
    return build_evaluation(
        spec,
        score=10.0,
        justification="No se impone arbitraje, o fue libremente negociado entre las partes.",
    )


async def evaluate_e8(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E8 — Limitation of seller/lessor liability (§8 E8)."""

    hit = patterns.find_first(ctx.contract_text, patterns.E8_LIABILITY_LIMITATION)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification="Cláusula de exoneración / limitación de responsabilidad detectada.",
            evidence_snippet=hit.snippet,
        )
    return build_evaluation(
        spec, score=10.0, justification="No se detecta limitación de responsabilidad del proveedor."
    )


async def evaluate_e9(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """E9 — Abusive penalty to consumer (§8 E9).

    Allows intermediate score 5 when the penalty is high but justified
    by the nature of the contract (e.g. customized product).
    """

    hit = patterns.find_first(ctx.contract_text, patterns.E9_DISPROPORTIONATE_PENALTY)
    if hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Penalidad desproporcionada al consumidor (p. ej. pérdida total de lo pagado por " "incumplir un mes)."
            ),
            evidence_snippet=hit.snippet,
        )
    elements = ctx.elements_detected or {}
    if elements.get("consumer_penalty_high_but_justified", False):
        return build_evaluation(
            spec,
            score=5.0,
            justification="Penalidad alta pero justificada por la naturaleza del contrato (§8 E9 banda 5).",
        )
    return build_evaluation(spec, score=10.0, justification="Penalidad proporcional al daño causado.")


CATEGORY_E_EVALUATORS = {
    "E1": evaluate_e1,
    "E2": evaluate_e2,
    "E3": evaluate_e3,
    "E4": evaluate_e4,
    "E5": evaluate_e5,
    "E6": evaluate_e6,
    "E7": evaluate_e7,
    "E8": evaluate_e8,
    "E9": evaluate_e9,
}


def register_category_e(registry) -> None:
    for criterion_id, fn in CATEGORY_E_EVALUATORS.items():
        registry.register(criterion_id, fn)


__all__ = [
    "CATEGORY_E_EVALUATORS",
    "evaluate_e1",
    "evaluate_e2",
    "evaluate_e3",
    "evaluate_e4",
    "evaluate_e5",
    "evaluate_e6",
    "evaluate_e7",
    "evaluate_e8",
    "evaluate_e9",
    "register_category_e",
]
