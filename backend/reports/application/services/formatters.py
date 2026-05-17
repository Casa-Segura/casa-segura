"""Spanish-locale formatters used across the section builders.

Centralized so the section-specific helpers (header, economic, footer)
share one source of truth and the templates stay declarative.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

_MONTHS_ES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)

_CONTRACT_TYPE_LABELS_ES = {
    "CVC": "Compraventa al contado",
    "CVP": "Compraventa a plazos",
    "ARV": "Arrendamiento de vivienda",
    "ARC": "Arrendamiento de local comercial",
    "APV": "Arrendamiento con promesa de venta",
    "LEA": "Arrendamiento financiero (leasing)",
    "IVU": "Contrato institucional IVU",
    "FSV": "Compra o préstamo financiado por FSV",
    "NOT_CLASSIFIABLE": "No clasificable",
}

_BAND_LABELS_ES = {
    "green": "Favorable",
    "yellow": "Negocia antes de firmar",
    "red": "Procede con cuidado",
    "not_analyzable": "No analizable",
}

_BAND_ICONS = {
    "green": "\U0001f7e2",  # 🟢
    "yellow": "\U0001f7e1",  # 🟡
    "red": "\U0001f534",  # 🔴
    "not_analyzable": "⚫",  # ⚫
}

_BAND_HEX = {
    "green": "#10B981",
    "yellow": "#F59E0B",
    "red": "#EF4444",
    "not_analyzable": "#6B7280",
}

PURCHASE_CONTRACT_TYPES = frozenset({"CVC", "CVP", "APV", "LEA", "FSV"})


def long_date_es(value: date | datetime) -> str:
    """Render a date as ``10 de mayo de 2026`` per PRD F6 §3 US-02."""

    if isinstance(value, datetime):
        value = value.date()
    return f"{value.day} de {_MONTHS_ES[value.month - 1]} de {value.year}"


def contract_type_label_es(code: str | None) -> str:
    if code is None:
        return "Tipo no determinado"
    return _CONTRACT_TYPE_LABELS_ES.get(code, code)


def band_label_es(code: str) -> str:
    return _BAND_LABELS_ES.get(code, code)


def band_icon(code: str) -> str:
    return _BAND_ICONS.get(code, "")


def band_hex(code: str) -> str:
    return _BAND_HEX.get(code, "#111111")


def money_usd_es(value: Decimal | float | int | None, *, fraction_digits: int = 2) -> str | None:
    if value is None:
        return None
    amount = Decimal(str(value))
    # Salvadoran convention: $ + thousands separator + decimal point.
    return f"${amount:,.{fraction_digits}f}"


def percent_es(value: Decimal | float | int | None, *, fraction_digits: int = 1) -> str | None:
    """Render a percentage. Accepts a fraction (0.18) or percent-points (18)."""

    if value is None:
        return None
    amount = Decimal(str(value))
    if Decimal("0") <= amount <= Decimal("1"):
        amount = amount * Decimal("100")
    return f"{amount:.{fraction_digits}f}%"


def months_to_years_es(months: int | float | Decimal | None) -> str | None:
    if months is None:
        return None
    years = Decimal(str(months)) / Decimal("12")
    return f"{years.normalize()} años".replace("0E-1", "0")


def multiplier_es(value: Decimal | float | None) -> str | None:
    if value is None:
        return None
    return f"{Decimal(str(value)):.2f}x del precio contado"


__all__ = [
    "PURCHASE_CONTRACT_TYPES",
    "band_hex",
    "band_icon",
    "band_label_es",
    "contract_type_label_es",
    "long_date_es",
    "money_usd_es",
    "months_to_years_es",
    "multiplier_es",
    "percent_es",
]
