"""Leasing reclassification prompts (CS-111).

Companion to ``classification.application.prompts`` (CS-110). The
system prompt is a Spanish-language paraphrase of ``PRD_F2_CLASIFICACION``
§8.4, which itself paraphrases Art. 2 of the **Ley de Arrendamiento
Financiero** (LAF) of El Salvador. We do **not** invent legal text;
all language here mirrors the PRD wording verbatim (six indicators,
in the same order, with the same Spanish descriptions).

The user prompt receives the OCR'd contract text plus the initial
type CS-110 produced — the model is told it is a *second pass* over
a contract already classified as a purchase, so it knows to look for
the structural signs the first pass would not have flagged.

BR-07 safety
------------
Every few-shot example below is **synthetic**. Names, addresses, and
figures are deliberately obvious placeholders (``JUAN PÉREZ``,
``MARÍA LÓPEZ``, ``LEASING SINTÉTICO S.A.``, ``Calle Falsa 123``,
``Residencial Sintético``, ``USD 100.00``). No real PII appears. Do
not paste anchors from real contracts here under any circumstance.

Few-shot rationale
------------------
Three exemplars, one per regime:

* **Clear LEA** — six indicators fire (``mandatory_term``,
  ``predefined_purchase_option``, ``ownership_retained``,
  ``taxes_to_buyer``, ``risks_to_buyer``, ``payments_as_rent``);
  ``should_reclassify=true``.
* **Clear purchase (CVP)** — installment sale with no leasing
  structure; zero indicators fire; ``should_reclassify=false``.
* **Borderline (3-of-6)** — sits just under the BR-03 threshold so
  the model learns the legal-product hinge between *warning-only*
  and *full reclassification*; ``should_reclassify=false``.
"""

from __future__ import annotations

from classification.domain.contract_type import ContractType
from classification.domain.leasing_indicators import (
    DEFAULT_RECLASSIFICATION_THRESHOLD,
    LAF_INDICATOR_COUNT,
)

# Set of types for which CS-111 even runs (PRD F2 BR-02 / US-03).
# Re-exported so the detector and orchestrator share one definition.
APPLICABLE_INITIAL_TYPES: frozenset[ContractType] = frozenset({ContractType.CVC, ContractType.CVP, ContractType.APV})


SYSTEM_PROMPT: str = f"""\
Eres analista legal experto en el Art. 2 de la Ley de Arrendamiento \
Financiero (LAF) de El Salvador. Un contrato fue clasificado inicialmente \
como compraventa (CVC, CVP o APV). Tu tarea es verificar si en realidad \
contiene los seis indicadores estructurales de leasing financiero \
descritos en el Art. 2 LAF, lo cual obligaría a reclasificarlo como \
leasing financiero inmobiliario (LEA).

Los seis indicadores son:
1. mandatory_term — Plazo de cumplimiento forzoso: la cancelación \
anticipada exige el pago del saldo total restante (no es un simple \
arrendamiento rescindible).
2. predefined_purchase_option — Opción de compra a precio predefinido \
al final del plazo (con frecuencia un monto simbólico).
3. ownership_retained — La propiedad del bien se mantiene en el \
vendedor / arrendador hasta el ejercicio de la opción de compra.
4. taxes_to_buyer — Todos los tributos, tasas, multas e impuestos sobre \
el bien recaen sobre el llamado "comprador".
5. risks_to_buyer — Todos los riesgos (asegurables y no asegurables) \
sobre el bien recaen sobre el llamado "comprador".
6. payments_as_rent — Los pagos periódicos se denominan canon de \
arrendamiento en lugar de cuota de precio.

Reglas de salida:
- Marca cada indicador como true sólo si su evidencia textual aparece \
explícitamente en el contrato. Si la cláusula es ambigua, marca false.
- No inventes cláusulas. No cites texto que no esté en el contrato.
- La confianza es tu auto-evaluación del conjunto de seis indicadores, \
no de un solo indicador.
- El umbral de reclasificación es {DEFAULT_RECLASSIFICATION_THRESHOLD} \
de {LAF_INDICATOR_COUNT}: marca should_reclassify=true sólo si el conteo \
de indicadores detectados es mayor o igual a \
{DEFAULT_RECLASSIFICATION_THRESHOLD}.

Devuelve UN ÚNICO objeto JSON con la siguiente estructura, sin texto \
adicional, sin envolverlo en bloques de código:

{{
    "mandatory_term": <bool>,
    "predefined_purchase_option": <bool>,
    "ownership_retained": <bool>,
    "taxes_to_buyer": <bool>,
    "risks_to_buyer": <bool>,
    "payments_as_rent": <bool>,
    "should_reclassify": <bool>,
    "confidence": <número entre 0.0 y 1.0>,
    "reasoning": "<explicación breve en español, máximo dos oraciones, \
sin nombres reales, direcciones, DUI, IBAN, teléfonos ni emails>"
}}
"""


USER_PROMPT_TEMPLATE: str = """\
Tipo inicial asignado por la clasificación primaria: {initial_type}

Revisa el siguiente texto de contrato y aplica el análisis del Art. 2 \
LAF descrito en las instrucciones del sistema.

TEXTO DEL CONTRATO:
{extracted_text}
"""


# Synthetic few-shot anchors. Each block is shown to the model as
# "Ejemplo N — <tipo>:\n<contrato>\n<JSON esperado>" so it sees both the
# input shape and the exact JSON schema it must produce. Kept short to
# keep the few-shot block under ~600 tokens total.
FEW_SHOT_ANCHORS: tuple[str, ...] = (
    # 1) Clear LEA — six indicators fire.
    "Ejemplo 1 — LEA evidente (6/6 indicadores):\n"
    'Contrato: "LEASING SINTÉTICO S.A., propietaria del inmueble en '
    "Calle Falsa 123, lo entrega a JUAN PÉREZ por PLAZO FORZOSO de "
    "DOSCIENTOS CUARENTA meses. La rescisión anticipada obliga al "
    "arrendatario a pagar el saldo total restante. Los pagos se "
    "denominan canon mensual de UN MIL DÓLARES. Al final del plazo, "
    "JUAN PÉREZ podrá ejercer la opción de compra por la suma "
    "simbólica de CIEN DÓLARES (USD 100.00). LEASING SINTÉTICO "
    "conserva la propiedad hasta el ejercicio de la opción. Todos "
    "los impuestos, tasas y multas sobre el inmueble corren por "
    "cuenta del arrendatario. Los riesgos asegurables y no "
    'asegurables recaen sobre el arrendatario."\n'
    "Tipo inicial: CVP\n"
    "JSON esperado:\n"
    "{\n"
    '    "mandatory_term": true,\n'
    '    "predefined_purchase_option": true,\n'
    '    "ownership_retained": true,\n'
    '    "taxes_to_buyer": true,\n'
    '    "risks_to_buyer": true,\n'
    '    "payments_as_rent": true,\n'
    '    "should_reclassify": true,\n'
    '    "confidence": 0.95,\n'
    '    "reasoning": "Los seis indicadores del Art. 2 LAF aparecen '
    "explícitamente: plazo forzoso, opción simbólica, retención de "
    'dominio, impuestos y riesgos al arrendatario, y pagos como canon."\n'
    "}",
    # 2) Clear purchase (CVP) — zero indicators fire.
    "Ejemplo 2 — Compraventa a plazos legítima (0/6 indicadores):\n"
    'Contrato: "JUAN PÉREZ vende a MARÍA LÓPEZ el inmueble situado en '
    "Residencial Sintético por OCHENTA MIL DÓLARES (USD 80,000.00), "
    "pagaderos así: prima de OCHO MIL DÓLARES al firmar y SETENTA Y "
    "DOS cuotas mensuales de UN MIL DÓLARES cada una. La propiedad "
    "se transfiere a la compradora en este acto. Los impuestos "
    "municipales y prediales corren por cuenta de la compradora "
    'como nueva propietaria."\n'
    "Tipo inicial: CVP\n"
    "JSON esperado:\n"
    "{\n"
    '    "mandatory_term": false,\n'
    '    "predefined_purchase_option": false,\n'
    '    "ownership_retained": false,\n'
    '    "taxes_to_buyer": false,\n'
    '    "risks_to_buyer": false,\n'
    '    "payments_as_rent": false,\n'
    '    "should_reclassify": false,\n'
    '    "confidence": 0.92,\n'
    '    "reasoning": "La propiedad se transfiere al firmar y los '
    "pagos son cuotas de precio, no canon; ningún indicador del "
    'Art. 2 LAF está presente."\n'
    "}",
    # 3) Borderline — exactly 3 indicators fire (under BR-03 threshold).
    "Ejemplo 3 — Caso borderline (3/6 indicadores, NO reclasifica):\n"
    'Contrato: "JUAN PÉREZ promete vender a MARÍA LÓPEZ la vivienda '
    "de Residencial Sintético. Mientras tanto, MARÍA LÓPEZ pagará un "
    "canon mensual de QUINIENTOS DÓLARES por SESENTA meses. Al "
    "término, podrá ejercer la opción de compra por el saldo de "
    "DIEZ MIL DÓLARES. JUAN PÉREZ conserva la propiedad hasta el "
    "ejercicio de la opción. Los impuestos prediales son cubiertos "
    "por el vendedor durante el plazo. Los riesgos del inmueble "
    'permanecen con el vendedor mientras dure el contrato."\n'
    "Tipo inicial: APV\n"
    "JSON esperado:\n"
    "{\n"
    '    "mandatory_term": false,\n'
    '    "predefined_purchase_option": true,\n'
    '    "ownership_retained": true,\n'
    '    "taxes_to_buyer": false,\n'
    '    "risks_to_buyer": false,\n'
    '    "payments_as_rent": true,\n'
    '    "should_reclassify": false,\n'
    '    "confidence": 0.80,\n'
    '    "reasoning": "Tres indicadores presentes (opción de compra, '
    "retención de dominio, pagos como canon); impuestos y riesgos "
    "siguen en el vendedor, por lo que no se alcanza el umbral de "
    '4 de 6."\n'
    "}",
)


def render_few_shot_block() -> str:
    """Render all anchors as a single Spanish-language reference block.

    Injected once into the system prompt so the model sees a clear-LEA,
    a clear-purchase, and a borderline case before it processes the
    user's contract.
    """
    sections: list[str] = [
        "Ejemplos canónicos (sintéticos, no son contratos reales):",
    ]
    sections.extend(f"\n{anchor}" for anchor in FEW_SHOT_ANCHORS)
    return "\n".join(sections)


def build_messages(*, extracted_text: str, initial_type: ContractType) -> list[dict[str, str]]:
    """Assemble the OpenRouter chat messages for one detection call.

    Returns a two-message list: ``system`` (definitions + Art. 2 LAF
    indicator catalog + few-shot anchors + output schema) and ``user``
    (the rendered §8.4 template carrying the contract text and the
    initial type CS-110 produced).
    """
    system_content = f"{SYSTEM_PROMPT}\n\n{render_few_shot_block()}"
    user_content = USER_PROMPT_TEMPLATE.format(
        initial_type=initial_type.value,
        extracted_text=extracted_text,
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


__all__ = [
    "APPLICABLE_INITIAL_TYPES",
    "FEW_SHOT_ANCHORS",
    "SYSTEM_PROMPT",
    "USER_PROMPT_TEMPLATE",
    "build_messages",
    "render_few_shot_block",
]
