"""Per-contract-type economic extraction prompts (CS-113).

Each prompt instructs the model to extract the **strict subset** of
:class:`~classification.domain.extracted_fields.ExtractedFields` that the
PRD requires for that ``ContractType`` — i.e. the per-type required set
declared in
:mod:`classification.application.extraction_policy.REQUIRED_FIELDS_BY_TYPE`.
Driving the prompt off that table guarantees the LLM is never asked for
fields the rubric does not need (cost) and never silently omits a field
the rubric does need (correctness).

Prompt design
-------------
Every prompt shares a **base prelude** that:

* Names the prompt's role ("analista financiero salvadoreño") so the
  model anchors on local terminology (cánones, prima, plazo, FSV, IVU).
* Restates PRD_F2 §8.5 conventions (USD default, historical ¢8.75 = $1
  for stray colón amounts, monthly-compounding derivation
  ``(1+r)^12 - 1``) so each per-type prompt does not have to repeat them.
* Restates the JSON-only output contract and the strict per-field shape:
  ``{<field>: {"value": <typed>, "confidence": 0..1, "rationale": "..."}}``.
* Enforces BR-07 safety: the prelude tells the model to NOT echo party
  names / addresses / DUI / NIT into the response (those live on
  ``ExtractedFields.seller_name`` etc. as transient holders, not on the
  extraction confidence map).

The per-type sections then enumerate ONLY the relevant fields, with
short Spanish descriptions cribbed from
``ExtractedFields.<field>.description``. The model sees a precise menu;
anything outside the menu is by construction not extracted, which
preserves CS-114's invariant that ``field_confidences`` keys are a
subset of ``ExtractedFields.model_fields``.

Few-shot examples
-----------------
We include ONE synthetic anchor per major type (CVC, CVP, ARV, LEA) per
the CS-113 minimum. Each anchor is **synthetic** (placeholder names,
addresses, and figures from the same vocabulary used in CS-110's
``FEW_SHOT_ANCHORS``) so the prompt corpus stays BR-07 safe.

NOT_CLASSIFIABLE
----------------
``ContractType.NOT_CLASSIFIABLE`` is intentionally absent from the
registry — the :class:`EconomicFieldExtractor` short-circuits before
ever looking up a prompt, returning an empty
:class:`~classification.domain.contract_extraction.ContractExtraction`.

PRD references:
    - PRD_F2_CLASIFICACION §8.5 (canonical economic field shapes).
    - PRD_F2_CLASIFICACION US-04 + BR-07 (missing → unverifiable).
    - PRD_F2_CLASIFICACION BR-08 (monthly → annual conversion).
"""

from __future__ import annotations

from typing import Final

from classification.application.extraction_policy import REQUIRED_FIELDS_BY_TYPE
from classification.domain.contract_type import ContractType
from classification.domain.extracted_fields import ExtractedFields

# --- Shared prelude ----------------------------------------------------

_BASE_PRELUDE: Final[str] = """\
Eres un analista financiero experto en contratos inmobiliarios salvadoreños. \
Tu tarea es extraer SOLAMENTE los campos económicos solicitados a partir del \
texto del contrato. No inventes valores, no interpretes más allá de lo \
literal, y no devuelvas campos que no se te pidan.

Convenciones (PRD F2 §8.5):
- Moneda: USD por defecto. Si el contrato usa colones (¢ o SVC), conviértelo \
a USD usando el tipo de cambio fijo histórico ¢8.75 = USD 1.00 y deja \
constancia en `rationale`.
- Porcentajes: devuélvelos como DECIMAL (ej. 0.09 para 9%). Si solo aparece \
una tasa mensual, calcula también la anual con capitalización mensual: \
`anual = (1 + mensual)^12 - 1` y deja constancia en `rationale`.
- Plazos: devuélvelos en MESES enteros (ej. 60 para "cinco años").
- Periodicidad: usa exactamente uno de `monthly`, `biweekly`, `weekly`, \
`other`.
- Base de cálculo de intereses: usa exactamente uno de \
`outstanding_principal`, `total_balance`, `unspecified`.

Privacidad (PRD F2 BR-07):
- NO copies nombres de personas, números de DUI, NIT, ni direcciones en el \
campo `rationale`. Cita únicamente la frase contractual mínima necesaria \
para justificar el valor extraído, anonimizando partes ("el vendedor", \
"la arrendataria") cuando aparezcan.

Formato de salida:
- Devuelve UN ÚNICO objeto JSON, sin texto adicional, sin bloques de código.
- La estructura debe ser exactamente:

{
    "<nombre_de_campo>": {
        "value": <número, entero, o cadena del enum según el campo>,
        "confidence": <número entre 0.0 y 1.0>,
        "rationale": "<máx. 300 caracteres, en español, sin PII>"
    },
    ...
}

- Si un campo solicitado NO aparece de forma explícita y verificable en el \
contrato, devuélvelo con `"value": null` y `"confidence": 0.0`. NUNCA \
inventes un valor para satisfacer el esquema.
- Si encuentras valores en conflicto para el mismo campo, devuelve \
`"value": null`, `"confidence": 0.0`, y explica el conflicto en \
`rationale`. No adivines.
"""

# --- Spanish descriptions per field ------------------------------------
#
# Sourced from `ExtractedFields.<field>.description` but rewritten in
# Spanish so the prompt does not need to translate at runtime. Keys MUST
# match attribute names on `ExtractedFields` — `_validate_field_specs`
# asserts this at import time.
_FIELD_SPECS: Final[dict[str, str]] = {
    "purchase_price_usd": ("Precio total declarado del inmueble en USD (número). PRD §8.5 " "`price_cash`."),
    "down_payment_usd": ("Monto de prima o anticipo en USD (número). PRD §8.5 `down_payment`."),
    "down_payment_pct": (
        "Prima expresada como FRACCIÓN DECIMAL en [0, 1] (ej. 0.10 para " "10%). PRD §8.5 `down_payment_pct`."
    ),
    "financed_amount_usd": ("Monto financiado en USD = precio - prima (número). PRD §8.5 " "`financed_amount`."),
    "monthly_payment_usd": ("Cuota mensual periódica en USD (número). PRD §8.5 " "`monthly_payment`."),
    "installment_count": ("Número total de cuotas, cuando el contrato lo expresa como conteo " "(entero)."),
    "term_months": ("Plazo total en MESES enteros (ej. 60 para cinco años). PRD §8.5 " "`term_months`."),
    "interest_rate_pct": (
        "Tasa anual efectiva como DECIMAL (ej. 0.09 para 9%). Si solo hay "
        "mensual, deriva con `(1+mensual)^12 - 1` y nótalo en `rationale`. "
        "PRD §8.5 `annual_rate_pct` + BR-08."
    ),
    "monthly_rate_pct": (
        "Tasa mensual como DECIMAL cuando el contrato solo declara la "
        "mensual (ej. 0.015 para 1.5%). PRD §8.5 `monthly_rate_pct`."
    ),
    "monthly_rent_usd": ("Canon o renta mensual en USD (número), para arrendamientos y " "leasing."),
    "deposit_usd": ("Depósito reembolsable en USD (número), típico en arrendamientos."),
    "purchase_option_price_usd": (
        "Precio de la opción de compra al final del plazo en USD (número), "
        "para LEA / APV. PRD F2 US-03 indicador Art. 2 LAF #2."
    ),
    "currency": (
        "Código de moneda reportado: usa `USD` por defecto, `SVC` si el "
        "contrato usa colones (tras la conversión histórica)."
    ),
    "payment_periodicity": ("Uno de: `monthly`, `biweekly`, `weekly`, `other`. PRD §8.5."),
    "interest_calculation_base": (
        "Uno de: `outstanding_principal` (si dice 'sobre saldo insoluto' o "
        "'sobre capital pendiente'), `total_balance` (si dice 'sobre saldo "
        "total' o 'sobre monto total adeudado'), `unspecified` (si no se "
        "menciona). `total_balance` dispara override Art. 12 LPC en F4."
    ),
    "project_name_raw": (
        "Nombre del proyecto inmobiliario tal y como aparece en el contrato "
        "(cadena). PRD F2 US-02 `canonical_name`."
    ),
    "property_address": ("Dirección del inmueble (cadena). TRANSITORIO: NO se persiste."),
    "seller_name": ("Nombre del vendedor / arrendador (cadena). TRANSITORIO: NO se " "persiste."),
    "buyer_name": ("Nombre del comprador / arrendatario (cadena). TRANSITORIO: NO se " "persiste."),
}


def _validate_field_specs() -> None:
    """Assert ``_FIELD_SPECS`` covers every attr ever required by any type.

    Runs at import time. A typo here would leak through as an unrendered
    field in the prompt — the LLM would silently omit it and the
    extractor would later flag it ``unverifiable`` for every contract,
    masking the bug.
    """
    known = set(ExtractedFields.model_fields.keys())
    unknown_in_specs = set(_FIELD_SPECS.keys()) - known
    if unknown_in_specs:
        raise RuntimeError(
            "economic_prompts._FIELD_SPECS references unknown "
            f"ExtractedFields attributes: {sorted(unknown_in_specs)}"
        )
    needed: set[str] = set()
    for required in REQUIRED_FIELDS_BY_TYPE.values():
        needed |= required
    missing_specs = needed - set(_FIELD_SPECS.keys())
    if missing_specs:
        raise RuntimeError(
            "economic_prompts._FIELD_SPECS is missing descriptions for " f"required fields: {sorted(missing_specs)}"
        )


_validate_field_specs()


# --- Few-shot anchors (BR-07-safe synthetic data) ----------------------
#
# One anchor per "major" type per CS-113. Anchors mirror the vocabulary
# used in `classification.application.prompts.FEW_SHOT_ANCHORS` (JUAN
# PÉREZ / MARÍA LÓPEZ / Residencial Sintético / Calle Falsa 123) so the
# corpus stays consistent across F2 prompts and is obviously synthetic.
_FEW_SHOT_ANCHORS: Final[dict[ContractType, str]] = {
    ContractType.CVC: (
        "Ejemplo CVC (sintético, sin PII real):\n"
        'Texto: "El comprador entrega en este acto la suma única de '
        "TREINTA MIL DÓLARES (USD 30,000.00) por el inmueble del "
        'Residencial Sintético. No existen cuotas ni saldo pendiente."\n'
        "Salida JSON:\n"
        "{\n"
        '  "purchase_price_usd": {"value": 30000.0, "confidence": 0.95, '
        '"rationale": "Precio único USD 30,000.00 pagado al firmar."},\n'
        '  "currency": {"value": "USD", "confidence": 0.99, '
        '"rationale": "Cifra expresada en DÓLARES."},\n'
        '  "project_name_raw": {"value": "Residencial Sintético", '
        '"confidence": 0.9, "rationale": "Proyecto citado literalmente."}\n'
        "}"
    ),
    ContractType.CVP: (
        "Ejemplo CVP (sintético, sin PII real):\n"
        'Texto: "Precio total OCHENTA MIL DÓLARES (USD 80,000.00), '
        "pagaderos: prima de OCHO MIL DÓLARES al firmar (10%), saldo en "
        "72 cuotas mensuales de UN MIL DÓLARES con interés del 1.5% "
        'mensual sobre saldo insoluto, directamente al vendedor."\n'
        "Salida JSON:\n"
        "{\n"
        '  "purchase_price_usd": {"value": 80000.0, "confidence": 0.95, '
        '"rationale": "Precio total USD 80,000.00."},\n'
        '  "down_payment_usd": {"value": 8000.0, "confidence": 0.95, '
        '"rationale": "Prima USD 8,000.00 al firmar."},\n'
        '  "financed_amount_usd": {"value": 72000.0, "confidence": 0.8, '
        '"rationale": "Saldo = precio - prima = 80000 - 8000."},\n'
        '  "term_months": {"value": 72, "confidence": 0.95, '
        '"rationale": "72 cuotas mensuales."},\n'
        '  "monthly_payment_usd": {"value": 1000.0, "confidence": 0.95, '
        '"rationale": "Cuotas mensuales de USD 1,000.00."},\n'
        '  "interest_rate_pct": {"value": 0.1956, "confidence": 0.7, '
        '"rationale": "Anual derivada (1+0.015)^12 - 1 ≈ 0.1956 (BR-08)."},\n'
        '  "interest_calculation_base": {"value": "outstanding_principal", '
        '"confidence": 0.9, "rationale": "Texto: sobre saldo insoluto."},\n'
        '  "payment_periodicity": {"value": "monthly", "confidence": 0.99, '
        '"rationale": "Cuotas mensuales."},\n'
        '  "currency": {"value": "USD", "confidence": 0.99, '
        '"rationale": "Cifras en DÓLARES."},\n'
        '  "project_name_raw": {"value": null, "confidence": 0.0, '
        '"rationale": "No se menciona el nombre del proyecto."}\n'
        "}"
    ),
    ContractType.ARV: (
        "Ejemplo ARV (sintético, sin PII real):\n"
        'Texto: "Se da en arrendamiento la vivienda del Residencial '
        "Sintético, canon mensual CUATROCIENTOS DÓLARES (USD 400.00), "
        "depósito de garantía CUATROCIENTOS DÓLARES, plazo de 12 meses "
        'prorrogable. Sin opción de compra."\n'
        "Salida JSON:\n"
        "{\n"
        '  "monthly_rent_usd": {"value": 400.0, "confidence": 0.98, '
        '"rationale": "Canon mensual USD 400.00."},\n'
        '  "deposit_usd": {"value": 400.0, "confidence": 0.95, '
        '"rationale": "Depósito de garantía USD 400.00."},\n'
        '  "term_months": {"value": 12, "confidence": 0.95, '
        '"rationale": "Plazo de 12 meses prorrogable."},\n'
        '  "payment_periodicity": {"value": "monthly", "confidence": 0.99, '
        '"rationale": "Canon mensual."},\n'
        '  "currency": {"value": "USD", "confidence": 0.99, '
        '"rationale": "Cifras en DÓLARES."},\n'
        '  "project_name_raw": {"value": "Residencial Sintético", '
        '"confidence": 0.9, "rationale": "Proyecto citado literalmente."}\n'
        "}"
    ),
    ContractType.LEA: (
        "Ejemplo LEA (sintético, sin PII real):\n"
        'Texto: "LEASING SINTÉTICO S.A. entrega en arrendamiento '
        "financiero el inmueble por plazo forzoso de 240 meses, canon "
        "mensual UN MIL DÓLARES (USD 1,000.00), con opción de compra al "
        "final por la suma simbólica de CIEN DÓLARES (USD 100.00). Tasa "
        'implícita anual del 9%."\n'
        "Salida JSON:\n"
        "{\n"
        '  "monthly_rent_usd": {"value": 1000.0, "confidence": 0.95, '
        '"rationale": "Canon mensual USD 1,000.00."},\n'
        '  "term_months": {"value": 240, "confidence": 0.98, '
        '"rationale": "Plazo forzoso de 240 meses."},\n'
        '  "purchase_option_price_usd": {"value": 100.0, "confidence": 0.95, '
        '"rationale": "Opción de compra al final por USD 100.00."},\n'
        '  "interest_rate_pct": {"value": 0.09, "confidence": 0.85, '
        '"rationale": "Tasa anual del 9% expresada como 0.09."},\n'
        '  "payment_periodicity": {"value": "monthly", "confidence": 0.99, '
        '"rationale": "Canon mensual."},\n'
        '  "currency": {"value": "USD", "confidence": 0.99, '
        '"rationale": "Cifras en DÓLARES."},\n'
        '  "project_name_raw": {"value": null, "confidence": 0.0, '
        '"rationale": "No se identifica el nombre del proyecto."}\n'
        "}"
    ),
}


# --- Prompt rendering --------------------------------------------------


def _render_field_menu(contract_type: ContractType) -> str:
    """Render the per-type field menu as a Spanish-language bullet list."""
    required = sorted(REQUIRED_FIELDS_BY_TYPE.get(contract_type, set()))
    if not required:
        return "(este tipo de contrato no requiere campos económicos)"
    bullets = [f"- `{name}`: {_FIELD_SPECS[name]}" for name in required]
    return "\n".join(bullets)


def _render_few_shot(contract_type: ContractType) -> str:
    """Render the few-shot anchor for ``contract_type`` if one is defined.

    Falls back to a generic CVP anchor (most field-rich) when the type
    does not have its own anchor — every prompt thus carries at least one
    worked example.
    """
    anchor = _FEW_SHOT_ANCHORS.get(contract_type)
    if anchor is None:
        anchor = _FEW_SHOT_ANCHORS[ContractType.CVP]
    return anchor


def build_economic_prompt(contract_type: ContractType) -> str:
    """Return the full system prompt for the given ``contract_type``.

    Concatenates the shared prelude, the per-type field menu (derived
    from :data:`REQUIRED_FIELDS_BY_TYPE`), and one synthetic few-shot
    anchor. The result is a single Spanish system message ready to be
    sent as ``{"role": "system", "content": <prompt>}``.

    Raises:
        KeyError: if the caller passes ``ContractType.NOT_CLASSIFIABLE``.
            The :class:`EconomicFieldExtractor` short-circuits before
            this point, but we surface the error to make accidental
            misuse loud at the boundary.
    """
    if contract_type is ContractType.NOT_CLASSIFIABLE:
        raise KeyError(
            "NOT_CLASSIFIABLE has no economic extraction prompt; "
            "the extractor must short-circuit before calling this."
        )
    menu = _render_field_menu(contract_type)
    few_shot = _render_few_shot(contract_type)
    return (
        f"{_BASE_PRELUDE}\n"
        f"Campos a extraer para un contrato tipo {contract_type.value}:\n"
        f"{menu}\n\n"
        f"{few_shot}\n"
    )


def build_user_prompt(extracted_text: str) -> str:
    """Render the user-turn message: the contract text under a header."""
    return (
        "Aquí está el texto extraído del contrato. Aplica las reglas y "
        "devuelve únicamente el objeto JSON solicitado.\n\n"
        "TEXTO DEL CONTRATO:\n"
        f"{extracted_text}\n"
    )


def build_messages(
    extracted_text: str,
    contract_type: ContractType,
) -> list[dict[str, str]]:
    """Assemble the OpenRouter chat messages for one economic extraction call."""
    return [
        {"role": "system", "content": build_economic_prompt(contract_type)},
        {"role": "user", "content": build_user_prompt(extracted_text)},
    ]


__all__ = [
    "build_economic_prompt",
    "build_messages",
    "build_user_prompt",
]
