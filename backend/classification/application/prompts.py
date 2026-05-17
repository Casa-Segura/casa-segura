"""Classification prompts and few-shot anchors (CS-110).

Prompt design
-------------
The system prompt is a Spanish-language definition of the eight covered
contract types plus ``NOT_CLASSIFIABLE`` (PRD F2 §8.1), followed by the
five classification rules verbatim from the PRD and a strict JSON output
contract. We append a curated ``FEW_SHOT_ANCHORS`` block — one tiny
synthetic exemplar per outcome — so the model sees a concrete instance
of every label before it ever runs on a real document. This trades a
small token budget for a large drop in label drift on edge cases
(APV vs LEA, IVU vs FSV, mid-confidence purchase contracts).

The user prompt is the §8.2 template with ``{extracted_text}``
substituted at call time. We keep the prompts in Spanish per the PRD's
"do not translate" guidance: the model is reasoning over Salvadoran
legal terminology that does not have crisp English analogs.

BR-07 safety
------------
Every anchor below is **synthetic**. Names, addresses, and figures are
deliberately obvious placeholders (``JUAN PÉREZ``, ``MARÍA LÓPEZ``,
``Calle Falsa 123``, ``Residencial Sintético``). There is no real PII.
Do not paste anchors from real contracts here under any circumstance.

Anchor rationale
----------------
Each anchor was chosen to expose the **single** clause that is most
diagnostic for its type under ``RUBRICA_CONTRATO`` §3:

* ``CVC``: lump-sum cash payment at signing (no installments).
* ``CVP``: explicit installment schedule, no leasing structure.
* ``ARV``: residential lease, monthly rent, no purchase option.
* ``ARC``: small commercial lease for a business unit.
* ``APV``: lease today, mandatory purchase option at term end,
  rent counts toward price.
* ``LEA``: financial leasing — financier owns the asset until the
  symbolic-price option is exercised (Art. 2 LAF anchor).
* ``IVU``: Instituto de Vivienda Urbana institutional adjudication
  with Bien de Familia regime.
* ``FSV``: Fondo Social para la Vivienda financing.
* ``NOT_CLASSIFIABLE``: a document type outside the eight (e.g. a
  donation), so the model is anchored on the rejection path too.
"""

from __future__ import annotations

from classification.domain.contract_type import ContractType

SYSTEM_PROMPT: str = """\
Eres un analista experto en contratos inmobiliarios salvadoreños. Tu tarea \
es clasificar un contrato en uno de los siguientes nueve resultados \
exclusivos.

Tipos válidos:
- CVC: Compraventa de inmueble al contado (precio se paga total al firmar o \
en muy corto plazo, sin financiamiento estructurado).
- CVP: Compraventa de inmueble a plazos (precio pagadero en cuotas con o sin \
intereses, directo con vendedor o desarrollador, sin que sea financiamiento \
bancario regulado).
- ARV: Arrendamiento de vivienda (alquiler de casa, apartamento, mesón, para \
habitación).
- ARC: Arrendamiento de local comercial pequeño (alquiler para negocio cuyo \
activo no excede el límite legal, generalmente con habitación adjunta).
- APV: Arrendamiento con promesa de venta (alquila ahora, comprar al final \
del plazo con cánones que computan a precio).
- LEA: Leasing financiero inmobiliario (entidad financiera o leasing house es \
dueña, usuario paga canon y al final tiene opción de compra a precio \
predefinido).
- IVU: Contrato institucional del Instituto de Vivienda Urbana (adjudicación \
o renta de vivienda con régimen Bien de Familia).
- FSV: Contrato de compraventa financiado por el Fondo Social para la \
Vivienda.
- NOT_CLASSIFIABLE: ninguno de los anteriores aplica claramente.

Reglas de clasificación:
1. Una compraventa al contado paga el precio total al momento de firmar la \
escritura. Si hay cuotas, es CVP.
2. Un arrendamiento de vivienda paga renta mensual sin opción de adquisición. \
Si hay opción, es APV.
3. Un leasing tiene tres partes: proveedor, arrendador financiero, y \
arrendatario. El arrendador es dueño hasta el ejercicio de la opción de \
compra.
4. Si el contrato menciona el Fondo Social para la Vivienda como financiador, \
es FSV.
5. Si el contrato menciona el Instituto de Vivienda Urbana, IVU, o régimen \
Bien de Familia institucional, es IVU.

Devuelve UN ÚNICO objeto JSON con la siguiente estructura, sin texto \
adicional, sin envolverlo en bloques de código:

{
    "contract_type": "<uno de los nueve códigos>",
    "confidence": <número entre 0.0 y 1.0>,
    "reasoning": "<explicación breve en español, máximo dos oraciones>"
}
"""


USER_PROMPT_TEMPLATE: str = """\
Aquí está el texto extraído de un contrato. Clasifícalo según las reglas \
dadas.

TEXTO DEL CONTRATO:
{extracted_text}
"""


# Each anchor is intentionally short (one to three clauses) so the
# few-shot block stays under a few hundred tokens total. They are
# synthetic — see the module docstring for BR-07 compliance notes.
FEW_SHOT_ANCHORS: dict[ContractType, str] = {
    ContractType.CVC: (
        "Ejemplo CVC — Compraventa al contado:\n"
        '"JUAN PÉREZ vende a MARÍA LÓPEZ el inmueble ubicado en Calle Falsa '
        "123, por el precio único de TREINTA MIL DÓLARES (USD 30,000.00) "
        "que la compradora entrega en este acto en su totalidad. No hay "
        'saldo pendiente ni cuotas."'
    ),
    ContractType.CVP: (
        "Ejemplo CVP — Compraventa a plazos:\n"
        '"El precio total del inmueble en Residencial Sintético es de '
        "OCHENTA MIL DÓLARES (USD 80,000.00), pagaderos así: prima de "
        "OCHO MIL DÓLARES al firmar y SETENTA Y DOS cuotas mensuales de "
        'UN MIL DÓLARES cada una directamente al vendedor JUAN PÉREZ."'
    ),
    ContractType.ARV: (
        "Ejemplo ARV — Arrendamiento de vivienda:\n"
        '"MARÍA LÓPEZ da en arrendamiento a JUAN PÉREZ la casa de '
        "habitación situada en Calle Falsa 123, por canon mensual de "
        "CUATROCIENTOS DÓLARES (USD 400.00), por plazo de doce meses "
        'prorrogable. El presente contrato no confiere opción de compra."'
    ),
    ContractType.ARC: (
        "Ejemplo ARC — Arrendamiento de local comercial pequeño:\n"
        '"MARÍA LÓPEZ arrienda a JUAN PÉREZ el local comercial número 2 '
        "ubicado en Calle Falsa 123, destinado exclusivamente al giro de "
        "pequeño comercio (pupusería), por canon mensual de TRESCIENTOS "
        'DÓLARES (USD 300.00) por plazo de un año."'
    ),
    ContractType.APV: (
        "Ejemplo APV — Arrendamiento con promesa de venta:\n"
        '"JUAN PÉREZ arrienda a MARÍA LÓPEZ la vivienda de Residencial '
        "Sintético, por canon mensual de QUINIENTOS DÓLARES por SESENTA "
        "meses. Al término del plazo, la arrendataria podrá ejercer la "
        "promesa de venta pagando un saldo de DIEZ MIL DÓLARES, "
        'imputándose los cánones al precio total."'
    ),
    ContractType.LEA: (
        "Ejemplo LEA — Leasing financiero inmobiliario:\n"
        '"LEASING SINTÉTICO S.A., propietaria del inmueble en Calle Falsa '
        "123, lo entrega en arrendamiento financiero a JUAN PÉREZ por "
        "PLAZO FORZOSO de DOSCIENTOS CUARENTA meses, mediante canon "
        "mensual de UN MIL DÓLARES. Al final del plazo, el arrendatario "
        "podrá ejercer la opción de compra por la suma simbólica de "
        "CIEN DÓLARES (USD 100.00). La propiedad permanece en LEASING "
        'SINTÉTICO hasta el ejercicio de la opción."'
    ),
    ContractType.IVU: (
        "Ejemplo IVU — Contrato institucional del Instituto de Vivienda "
        "Urbana:\n"
        '"El Instituto de Vivienda Urbana adjudica a JUAN PÉREZ la '
        "vivienda número 7 del Bloque B, bajo el régimen institucional "
        "de Bien de Familia, con cuota mensual de CIENTO CINCUENTA "
        'DÓLARES por el plazo institucional vigente."'
    ),
    ContractType.FSV: (
        "Ejemplo FSV — Compraventa financiada por el Fondo Social para la "
        "Vivienda:\n"
        '"JUAN PÉREZ adquiere la vivienda situada en Residencial '
        "Sintético por SESENTA MIL DÓLARES, de los cuales el Fondo "
        "Social para la Vivienda financia CINCUENTA Y CUATRO MIL "
        "DÓLARES a CIENTO OCHENTA meses plazo, conforme la normativa "
        'del FSV."'
    ),
    ContractType.NOT_CLASSIFIABLE: (
        "Ejemplo NOT_CLASSIFIABLE — Donación (fuera del alcance):\n"
        '"JUAN PÉREZ dona pura, simple e irrevocablemente a MARÍA LÓPEZ '
        "el inmueble situado en Calle Falsa 123, sin contraprestación "
        'alguna." Este documento es una donación, no una compraventa ni '
        "arrendamiento ni leasing, por lo que se devuelve "
        "NOT_CLASSIFIABLE."
    ),
}


def render_few_shot_block() -> str:
    """Render all anchors as a single Spanish-language reference block.

    The block is injected once into the system prompt so the model sees
    every label before it sees the user's contract.
    """
    sections = [
        "Ejemplos canónicos (sintéticos, no son contratos reales):",
    ]
    for contract_type, anchor in FEW_SHOT_ANCHORS.items():
        sections.append(f"\n[{contract_type.value}]\n{anchor}")
    return "\n".join(sections)


def build_messages(extracted_text: str) -> list[dict[str, str]]:
    """Assemble the OpenRouter chat messages for a single classification call.

    Returns a two-message list: ``system`` (definitions + rules + few-shot
    anchors + output schema) and ``user`` (the rendered §8.2 template).
    """
    system_content = f"{SYSTEM_PROMPT}\n\n{render_few_shot_block()}"
    user_content = USER_PROMPT_TEMPLATE.format(extracted_text=extracted_text)
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


# ---------------------------------------------------------------------------
# §8.3 validation prompt — invoked when the primary call lands in the
# medium-confidence band (PRD F2 §US-01). The validator is given the
# *prior* classification + reasoning and is asked to confirm or reject it.
# It is NOT a fresh pass: the goal is to surface disagreement, not to
# average two opinions.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_VALIDATION: str = """\
Eres un revisor experto en clasificación de contratos inmobiliarios \
salvadoreños. Otro analista ya clasificó el contrato pero con confianza \
intermedia. Tu tarea es validar — confirmar o rechazar — su decisión.

Procedimiento estricto:
1. Lee el tipo y razonamiento previos.
2. Lee el texto del contrato.
3. Decide si el tipo declarado se sostiene con la evidencia. Si SÍ, \
devuelve el mismo `contract_type` con tu propia confianza. Si NO, devuelve \
el `contract_type` que consideres correcto (o NOT_CLASSIFIABLE) con tu \
confianza.

No promedies opiniones. No "suavices" la confianza. Devuelve tu lectura \
independiente.

Tipos válidos: CVC, CVP, ARV, ARC, APV, LEA, IVU, FSV, NOT_CLASSIFIABLE.

Devuelve UN ÚNICO objeto JSON sin texto adicional ni bloques de código:

{
    "contract_type": "<uno de los nueve códigos>",
    "confidence": <número entre 0.0 y 1.0>,
    "reasoning": "<explicación breve en español, máximo dos oraciones>"
}
"""


USER_PROMPT_VALIDATION_TEMPLATE: str = """\
Clasificación previa: {prior_type}
Razonamiento previo: {prior_reasoning}

TEXTO DEL CONTRATO:
{extracted_text}

¿Sostienes la clasificación previa con la evidencia disponible?
"""


def build_validation_messages(
    extracted_text: str,
    *,
    prior_type: str,
    prior_reasoning: str | None,
) -> list[dict[str, str]]:
    """Assemble the §8.3 validation chat messages.

    The system prompt is independent of the primary call so the model
    cannot anchor on the few-shot block; the prior classification is
    surfaced in the user message instead.
    """
    user_content = USER_PROMPT_VALIDATION_TEMPLATE.format(
        prior_type=prior_type,
        prior_reasoning=(prior_reasoning or "(no proporcionado)"),
        extracted_text=extracted_text,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT_VALIDATION},
        {"role": "user", "content": user_content},
    ]
