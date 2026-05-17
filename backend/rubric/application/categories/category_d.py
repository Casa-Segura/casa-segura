"""Category D evaluators — D1..D6 (CS-162).

Property/registry risks per RUBRICA_CONTRATO §7. D2 emits the
``art_3_ivu_family_homestead`` override; D3 emits ``art_58_fsv``. D6
ships with ``provisional_pending_corpus=true`` metadata until the
Lotificaciones law is incorporated verbatim into the corpus.
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


async def evaluate_d1(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """D1 — Declared registry status (§7 D1)."""

    elements = ctx.elements_detected or {}
    status = elements.get("registry_status_disclosure")
    table = {
        "matricula_with_proof": (10.0, "Matrícula, libro, folio declarados con prueba adjunta."),
        "free_of_liens_no_proof": (7.0, "Declara libre de gravámenes pero sin prueba adjunta."),
        "superficial_mention": (3.0, "Mención superficial del estado del inmueble (§7 D1 banda 3)."),
        "omitted": (0.0, "El contrato omite toda mención al estado registral (§7 D1 banda 0)."),
    }
    if status in table:
        score, justification = table[status]
        return build_evaluation(spec, score=score, justification=justification)
    return build_evaluation(spec, score=3.0, justification="Estado registral declarado de manera incompleta.")


async def evaluate_d2(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """D2 — Bien de Familia regime (§7 D2 + Art. 3 Ley IVU override)."""

    text = ctx.contract_text
    bien_hit = patterns.find_first(text, patterns.D2_BIEN_DE_FAMILIA)
    transfer_hit = patterns.find_first(text, patterns.D2_TRANSFER_ATTEMPT)

    elements = ctx.elements_detected or {}
    regime_lapsed = elements.get("bien_de_familia_regime_lapsed", False)
    cancellation_deed_shown = elements.get("bien_de_familia_cancellation_deed", False)

    if bien_hit is not None and transfer_hit is not None and not (regime_lapsed or cancellation_deed_shown):
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Intento de transferir propiedad bajo Bien de Familia sin cancelación previa — "
                "Art. 3 Ley IVU declara nulidad absoluta."
            ),
            evidence_snippet=bien_hit.snippet,
            override_triggered=OverrideCode.ART_3_IVU_FAMILY_HOMESTEAD,
        )

    if bien_hit is None:
        return build_evaluation(
            spec,
            score=10.0,
            justification="Inmueble no se identifica bajo régimen de Bien de Familia.",
        )
    return build_evaluation(
        spec,
        score=10.0,
        justification=("Régimen de Bien de Familia presente pero ya cancelado o caducado (§7 D2 banda 10)."),
    )


async def evaluate_d3(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """D3 — Preventive FSV annotation (§7 D3 + Art. 58 Ley FSV override)."""

    text = ctx.contract_text
    declared = patterns.find_first(text, patterns.D3_FSV_DECLARED)
    no_consent = patterns.find_first(text, patterns.D3_FSV_NO_CONSENT)

    if declared is not None and no_consent is not None:
        return build_evaluation(
            spec,
            score=0.0,
            justification=(
                "Contrato declara anotación FSV pero no presenta autorización del Fondo — Art. 58 "
                "Ley FSV impide inscripción."
            ),
            evidence_snippet=(no_consent or declared).snippet,
            override_triggered=OverrideCode.ART_58_FSV,
        )

    elements = ctx.elements_detected or {}
    if elements.get("fsv_no_annotation_or_consent_letter_shown", False):
        return build_evaluation(
            spec, score=10.0, justification="Declara ausencia de anotación FSV o adjunta consentimiento."
        )
    return build_evaluation(
        spec,
        score=5.0,
        justification=(
            "Silencio sobre anotación FSV — no verificable; el usuario debe consultar el Registro (§7 D3)."
        ),
    )


async def evaluate_d4(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """D4 — Urbanism and construction permit (§7 D4)."""

    elements = ctx.elements_detected or {}
    posture = elements.get("permit_disclosure")
    table = {
        "valid_with_number_and_authority": (10.0, "Permiso citado con número, autoridad y vigencia (§7 D4 banda 10)."),
        "cited_dubious_format": (6.0, "Permiso citado con formato dudoso o sin fecha."),
        "generic_mention": (3.0, "Mención genérica del permiso (§7 D4 banda 3)."),
        "absent_or_stale": (0.0, "Sin permiso o permiso vencido sin evidencia de continuidad de obra."),
    }
    if posture in table:
        score, justification = table[posture]
        return build_evaluation(spec, score=score, justification=justification)
    return build_evaluation(spec, score=3.0, justification="Estado del permiso de construcción no claro.")


async def evaluate_d5(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """D5 — Registered responsible professional (§7 D5)."""

    elements = ctx.elements_detected or {}
    posture = elements.get("responsible_professional")
    table = {
        "full_id_with_registry_number": (10.0, "Nombre y número de registro del profesional responsable."),
        "name_without_registry": (6.0, "Nombre del profesional pero sin número de registro."),
        "generic_company_mention": (3.0, "Mención genérica ('la constructora') sin profesional identificado."),
        "absent": (0.0, "Sin identificación del responsable."),
    }
    if posture in table:
        score, justification = table[posture]
        return build_evaluation(spec, score=score, justification=justification)
    return build_evaluation(spec, score=3.0, justification="Profesional responsable no identificado con claridad.")


async def evaluate_d6(spec: CriterionSpec, ctx: EvaluationContext) -> CriterionEvaluation:
    """D6 — Regularized subdivision (§7 D6, provisional)."""

    elements = ctx.elements_detected or {}
    posture = elements.get("subdivision_status")
    table = {
        "registered": (10.0, "Lotificación registrada (§7 D6 banda 10)."),
        "regularization_declared_no_doc": (6.0, "Regularización declarada pero sin documentación adjunta."),
        "pre_september_2012": (3.0, "Lotificación previa a 2012 — sujeta a regularización con restricciones."),
        "unregistered": (0.0, "Lote sin registro ni proceso de regularización."),
    }
    if posture in table:
        score, justification = table[posture]
        evaluation = build_evaluation(spec, score=score, justification=justification)
        return evaluation
    # Default unverifiable + provisional flag (no synthetic citation per CS-162).
    return build_evaluation(
        spec,
        score=spec.worst_case_when_unverifiable,
        justification=(
            "[provisional_pending_corpus] Ley de Lotificaciones aún no incorporada verbatim — "
            "se aplica caso peor del catálogo y se solicita verificación legal."
        ),
        unverifiable=True,
    )


CATEGORY_D_EVALUATORS = {
    "D1": evaluate_d1,
    "D2": evaluate_d2,
    "D3": evaluate_d3,
    "D4": evaluate_d4,
    "D5": evaluate_d5,
    "D6": evaluate_d6,
}


def register_category_d(registry) -> None:
    for criterion_id, fn in CATEGORY_D_EVALUATORS.items():
        registry.register(criterion_id, fn)


__all__ = [
    "CATEGORY_D_EVALUATORS",
    "evaluate_d1",
    "evaluate_d2",
    "evaluate_d3",
    "evaluate_d4",
    "evaluate_d5",
    "evaluate_d6",
    "register_category_d",
]
