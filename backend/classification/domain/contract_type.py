"""Contract type enumeration (CS-110).

The canonical set of outcomes the classifier may emit is defined in
``PRD_F2_CLASIFICACION`` §8.1 (Tipos válidos) and ``RUBRICA_CONTRATO`` §3.
Exactly nine outcomes are allowed: eight covered contract types plus
``NOT_CLASSIFIABLE`` for the rejection path described in PRD F2 US-06.

Codes are the three-letter Spanish acronyms used across the rubric, the
DB schema (``contract_analysis.contract_type``), and the prompts. They
are intentionally short so they survive LLM round-trips without
case-folding ambiguity.

DDD note: this module lives in ``domain`` and therefore must NOT import
infrastructure (Django, httpx, etc.). It uses the stdlib ``enum`` rather
than ``django.db.models.TextChoices`` so the domain layer stays portable.
The Django-side ``TextChoices`` mirror — if and when it lands per the
Phase 2 implementation plan — should derive its values from this enum.
"""

from __future__ import annotations

from enum import StrEnum


class ContractType(StrEnum):
    """Closed set of contract classification outcomes (PRD F2 §8.1, BR-01).

    Values are the persisted codes. Labels are descriptive only.
    """

    CVC = "CVC"
    """Compraventa de inmueble al contado."""

    CVP = "CVP"
    """Compraventa de inmueble a plazos."""

    ARV = "ARV"
    """Arrendamiento de vivienda."""

    ARC = "ARC"
    """Arrendamiento de local comercial pequeño."""

    APV = "APV"
    """Arrendamiento con promesa de venta."""

    LEA = "LEA"
    """Leasing financiero inmobiliario (Ley de Arrendamiento Financiero)."""

    IVU = "IVU"
    """Contrato institucional del Instituto de Vivienda Urbana."""

    FSV = "FSV"
    """Contrato financiado por el Fondo Social para la Vivienda."""

    NOT_CLASSIFIABLE = "NOT_CLASSIFIABLE"
    """Ninguno de los ocho tipos cubiertos aplica (PRD F2 US-06)."""

    @classmethod
    def values(cls) -> list[str]:
        """Return all enum values as plain strings (useful for prompt rendering)."""
        return [member.value for member in cls]
