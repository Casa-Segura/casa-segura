"""Category A evaluators — A1..A6 (CS-159).

Per RUBRICA_CONTRATO §4 and §16. Each evaluator follows the same shape:

1. Look at ``contract_text`` for the rubric's pattern cues.
2. Pin the score per the §4 scale.
3. Emit the override (``art_1605_cc``, ``art_1613_cc``, ``art_1425_cc``)
   when the rubric forces a zero with a critical code.

These deterministic evaluators are the *short* path. The LLM-based
evaluator (``llm_evaluator.py``) replaces them at runtime for nuanced
contracts; the deterministic path is what the BVA tests pin.
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

PURCHASE_TYPES = {"CVC", "CVP", "APV"}


async def evaluate_a1(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """A1 — Written form and complete property data (§4 A1).

    Override ``art_1605_cc`` triggers when a CVC/CVP/APV contract lacks a
    public deed.
    """

    text = ctx.contract_text
    has_deed = patterns.any_match(text, patterns.A1_PUBLIC_DEED)
    simple_private_hit = patterns.find_first(text, patterns.A1_SIMPLE_PRIVATE)

    if ctx.contract_type in PURCHASE_TYPES and not has_deed:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Contrato de compraventa o promesa sin escritura pública otorgada ante notario "
                "(RUBRICA_CONTRATO §4 A1, Art. 1605 CC)."
            ),
            evidence_snippet=(simple_private_hit.snippet if simple_private_hit else None),
            override_triggered=OverrideCode.ART_1605_CC,
        )
    if has_deed and ctx.contract_type in PURCHASE_TYPES:
        return build_evaluation(
            spec,
            score=10.0,
            justification="Escritura pública identificada con descripción completa del inmueble.",
        )
    # Lease branch
    return build_evaluation(
        spec,
        score=8.0,
        justification=("Contrato de arrendamiento por escrito con datos básicos del inmueble (§4 A1 banda 8)."),
    )


async def evaluate_a2(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """A2 — Identification of the parties (§4 A2).

    Uses elements_detected slot ``parties_identified_count`` (0..2) and
    ``parties_missing_fields`` when supplied. With no signal, default to
    the rubric's middle score (7).
    """

    elements = ctx.elements_detected or {}
    parties = elements.get("parties_identified_count")
    missing = elements.get("parties_missing_fields_count")

    if parties == 0:
        return build_evaluation(
            spec,
            score=0.0,
            justification="Una de las partes no está identificada o carece de poderes acreditados.",
        )
    if missing is None:
        return build_evaluation(
            spec,
            score=7.0,
            justification=("Identificación de partes parcial — falta confirmar datos como DUI o domicilio."),
        )
    if missing == 0:
        return build_evaluation(
            spec,
            score=10.0,
            justification="Ambas partes identificadas con nombre, DUI/NIT, domicilio y profesión.",
        )
    if missing == 1:
        return build_evaluation(
            spec,
            score=7.0,
            justification="Falta DUI o domicilio de una de las partes (§4 A2 banda 7).",
        )
    return build_evaluation(
        spec,
        score=4.0,
        justification="Faltan dos o más datos de identificación (§4 A2 banda 4).",
    )


async def evaluate_a3(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """A3 — Determined price and payment form (§4 A3).

    Override ``art_1613_cc`` triggers when the price is at the seller's
    discretion.
    """

    discretionary_hit = patterns.find_first(ctx.contract_text, patterns.A3_DISCRETIONARY_PRICE)
    if discretionary_hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Cláusula que deja el precio al arbitrio de una de las partes (RUBRICA_CONTRATO §4 A3, Art. 1613 CC)."
            ),
            evidence_snippet=discretionary_hit.snippet,
            override_triggered=OverrideCode.ART_1613_CC,
        )
    economic = ctx.economic_summary or {}
    price = (economic.get("fields_extracted") or {}).get("price_cash")
    if price is not None:
        return build_evaluation(
            spec,
            score=10.0,
            justification="Precio total y forma de pago expresados con claridad.",
        )
    return build_evaluation(
        spec,
        score=7.0,
        justification=("Precio mencionado pero falta detalle (forma efectiva, tasa anual o periodicidad)."),
    )


async def evaluate_a4(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """A4 — Term and validity (§4 A4)."""

    economic = ctx.economic_summary or {}
    term = (economic.get("fields_extracted") or {}).get("term_months")
    elements = ctx.elements_detected or {}
    has_termination = elements.get("termination_form_present", False)

    if term is None:
        return build_evaluation(
            spec,
            score=0.0,
            justification="Sin plazo o término indeterminado en el contrato (§4 A4 banda 0).",
        )
    try:
        years = float(term) / 12.0
    except (TypeError, ValueError):
        years = 0.0
    if years > 30:
        return build_evaluation(
            spec,
            score=3.0,
            justification="Plazo excede el máximo legal aplicable o resulta ambiguo (§4 A4 banda 3).",
        )
    if has_termination:
        return build_evaluation(
            spec,
            score=10.0,
            justification="Plazo cierto y forma de terminación especificada (§4 A4 banda 10).",
        )
    return build_evaluation(
        spec,
        score=6.0,
        justification="Plazo presente pero no se especifica forma de terminación (§4 A4 banda 6).",
    )


async def evaluate_a5(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """A5 — Signature, date, and place (§4 A5)."""

    elements = ctx.elements_detected or {}
    signature = bool(elements.get("has_signature", False))
    date = bool(elements.get("has_date", False))
    place = bool(elements.get("has_place", False))
    score_components = sum(1 for present in (signature, date, place) if present)

    if score_components == 3:
        return build_evaluation(spec, score=10.0, justification="Firma, fecha y lugar presentes.")
    if score_components == 2:
        return build_evaluation(spec, score=6.0, justification="Falta uno de tres: firma, fecha o lugar.")
    return build_evaluation(
        spec,
        score=0.0,
        justification="Sin firma o sin fecha — incumple Art. 18 Ley de Inquilinato.",
    )


async def evaluate_a6(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """A6 — Valid promise to sell (§4 A6).

    Override ``art_1425_cc`` when the promise lacks term or condition.
    """

    promise_hit = patterns.find_first(ctx.contract_text, patterns.A6_PROMISE_WITHOUT_TERM)
    if promise_hit is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Promesa de venta sin plazo o condición que fije la época de la ejecución "
                "(RUBRICA_CONTRATO §4 A6, Art. 1425 CC)."
            ),
            evidence_snippet=promise_hit.snippet,
            override_triggered=OverrideCode.ART_1425_CC,
        )

    elements = ctx.elements_detected or {}
    requirements_met = int(elements.get("art_1425_requirements_met", 4))
    if requirements_met >= 4:
        return build_evaluation(
            spec,
            score=10.0,
            justification="Promesa cumple los cuatro requisitos del Art. 1425 CC.",
        )
    if requirements_met == 3:
        return build_evaluation(spec, score=7.0, justification="Falta uno de los cuatro requisitos del Art. 1425 CC.")
    if requirements_met == 2:
        return build_evaluation(spec, score=4.0, justification="Faltan dos de los cuatro requisitos del Art. 1425 CC.")
    return build_evaluation(spec, score=0.0, justification="Promesa con menos de dos requisitos del Art. 1425 CC.")


CATEGORY_A_EVALUATORS = {
    "A1": evaluate_a1,
    "A2": evaluate_a2,
    "A3": evaluate_a3,
    "A4": evaluate_a4,
    "A5": evaluate_a5,
    "A6": evaluate_a6,
}


def register_category_a(registry) -> None:
    for criterion_id, fn in CATEGORY_A_EVALUATORS.items():
        registry.register(criterion_id, fn)


__all__ = [
    "CATEGORY_A_EVALUATORS",
    "evaluate_a1",
    "evaluate_a2",
    "evaluate_a3",
    "evaluate_a4",
    "evaluate_a5",
    "evaluate_a6",
    "register_category_a",
]
