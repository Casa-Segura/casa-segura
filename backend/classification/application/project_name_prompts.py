"""Project-name extraction prompts (CS-112).

The classifier in CS-110 already extracts `project_name_canonical` as part
of its combined classification call (PRD F2 §8.1). CS-112 ships a *focused*
fallback / standalone prompt that can be invoked when:

* The combined call returned `project_name_canonical = null` and we want a
  second opinion before falling back to `unknown_<short_hash>`.
* The pipeline runs the extractor independently of classification (e.g.
  the QA endpoint `POST /v1/internal/classify`).

Prompt design
-------------
Spanish, deterministic-leaning (caller pins ``temperature=0.1``), with a
narrow JSON output contract: ``{"project_name_raw": str | null,
"confidence": float}``. The system prompt is explicit about what counts as
a *project* name vs. company / party / address names — this is the
single most common failure mode for Salvadoran real estate contracts,
which routinely name the developer (e.g. ``Constructora ACME, S.A. de
C.V.``) in the same paragraph as the project (``Residencial Los Ébanos``).

BR-07 safety
------------
Few-shot anchors are **synthetic**. Names, addresses, and developer names
are obvious placeholders (``Residencial Sintético``, ``Constructora
PLACEHOLDER S.A. de C.V.``, ``Calle Falsa 123``). Do not paste real
contract excerpts here under any circumstance.
"""

from __future__ import annotations


SYSTEM_PROMPT: str = """\
Eres un analista experto en contratos inmobiliarios salvadoreños. Tu \
única tarea en esta llamada es identificar el nombre del PROYECTO \
INMOBILIARIO al que pertenece el inmueble objeto del contrato.

Qué cuenta como nombre de proyecto:
- Nombre de la urbanización, residencial, condominio, lotificación, \
complejo o parque (por ejemplo: "Residencial Los Ébanos", "Condominio \
Arrecife 2", "Lotificación El Roble").
- Nombre comercial bajo el cual se vende un conjunto habitacional o \
comercial.
- El nombre puede aparecer en mayúsculas, con o sin acentos, en cualquier \
parte del contrato (encabezado, descripción del inmueble, cláusulas).

Qué NO cuenta como nombre de proyecto (y debes ignorar):
- Razón social de la empresa vendedora, desarrolladora, constructora, \
arrendadora financiera o promotora (por ejemplo: "Constructora ACME, \
S.A. de C.V.", "Leasing Sintético S.A.", "Inversiones XYZ").
- Nombre de las partes (vendedor, comprador, arrendador, arrendatario).
- Dirección, colonia, municipio, departamento o cantón por sí solos.
- Número o letra del lote, polígono, manzana o apartamento aislados.
- Nombre del banco financiador o de la institución (FSV, IVU).

Si el contrato menciona varios nombres candidatos, elige el que \
identifica el conjunto inmobiliario donde se ubica el inmueble. Si no \
hay un nombre de proyecto claro, devuelve null — es preferible no \
extraer a inventar.

Devuelve UN ÚNICO objeto JSON con exactamente esta estructura, sin \
texto adicional, sin envolverlo en bloques de código:

{
    "project_name_raw": "<nombre verbatim como aparece, o null>",
    "confidence": <número entre 0.0 y 1.0>
}
"""


USER_PROMPT_TEMPLATE: str = """\
Aquí está el texto extraído de un contrato. Identifica el nombre del \
proyecto inmobiliario según las reglas dadas.

TEXTO DEL CONTRATO:
{extracted_text}
"""


# Three synthetic anchors covering: clear hit, no hit, ambiguous hit.
# All names are obvious placeholders (BR-07 compliance).
FEW_SHOT_ANCHORS: list[dict[str, str]] = [
    {
        "label": "caso_claro",
        "extracted_text": (
            "JUAN PÉREZ vende a MARÍA LÓPEZ el inmueble identificado como "
            "Lote 7, Polígono B, del proyecto Residencial Los Ébanos, "
            "ubicado en Calle Falsa 123, municipio sintético. Vendedora: "
            "Constructora PLACEHOLDER, S.A. de C.V."
        ),
        "expected_json": (
            '{"project_name_raw": "Residencial Los Ébanos", "confidence": 0.95}'
        ),
        "explanation": (
            "El nombre del proyecto es 'Residencial Los Ébanos'. "
            "'Constructora PLACEHOLDER' es la razón social de la vendedora "
            "y no debe extraerse."
        ),
    },
    {
        "label": "caso_sin_proyecto",
        "extracted_text": (
            "MARÍA LÓPEZ da en arrendamiento a JUAN PÉREZ la casa de "
            "habitación situada en Calle Falsa 123, número 45, municipio "
            "sintético, por canon mensual de CUATROCIENTOS DÓLARES."
        ),
        "expected_json": '{"project_name_raw": null, "confidence": 0.90}',
        "explanation": (
            "El contrato sólo da una dirección postal; no menciona ninguna "
            "urbanización, residencial, condominio ni proyecto. Devolver "
            "null es preferible a inventar."
        ),
    },
    {
        "label": "caso_ambiguo",
        "extracted_text": (
            "Compraventa del inmueble en Calle Falsa 123, identificado en "
            "los planos como 'Las Palmeras II'. La vendedora es "
            "Constructora PLACEHOLDER, S.A. de C.V., que desarrolla el "
            "complejo habitacional Sintético Norte."
        ),
        "expected_json": (
            '{"project_name_raw": "Las Palmeras II", "confidence": 0.55}'
        ),
        "explanation": (
            "Hay dos candidatos: 'Las Palmeras II' (identifica el inmueble) "
            "y 'Sintético Norte' (otro proyecto de la misma constructora). "
            "Se prefiere el que identifica el inmueble del contrato, con "
            "confianza media porque hay ambigüedad."
        ),
    },
]


def render_few_shot_block() -> str:
    """Render the synthetic anchors as a single Spanish-language block."""
    sections = [
        "Ejemplos canónicos (sintéticos, no son contratos reales):",
    ]
    for anchor in FEW_SHOT_ANCHORS:
        sections.append(
            "\n"
            f"[{anchor['label']}]\n"
            f"TEXTO:\n{anchor['extracted_text']}\n"
            f"RESPUESTA:\n{anchor['expected_json']}\n"
            f"Justificación interna (no la devuelvas en la respuesta real): "
            f"{anchor['explanation']}"
        )
    return "\n".join(sections)


def build_messages(extracted_text: str) -> list[dict[str, str]]:
    """Assemble the OpenRouter chat messages for a project-name extraction call.

    Mirrors the shape used by `classification.application.prompts.build_messages`
    so the two services can share the same OpenRouter plumbing.
    """
    system_content = f"{SYSTEM_PROMPT}\n\n{render_few_shot_block()}"
    user_content = USER_PROMPT_TEMPLATE.format(extracted_text=extracted_text)
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


__all__ = [
    "FEW_SHOT_ANCHORS",
    "SYSTEM_PROMPT",
    "USER_PROMPT_TEMPLATE",
    "build_messages",
    "render_few_shot_block",
]
