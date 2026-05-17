"""F5 US-06 warning code → `EconomicWarning` translation (CS-135).

The submodules CS-131..CS-134 emit short string codes (`warning_precursors`)
that the assembler turns into structured `EconomicWarning(code,
severity_suggested, description, related_field)` rows per the cross-team
`ECONOMIC_SUMMARY_CONTRACT.md` shape.

Spanish copy is intentionally short and verbatim from PRD_F5 US-06; the
report-generation epic (EPIC-07) may extend or override these on rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Severity = Literal["yellow", "red"]


@dataclass(frozen=True)
class WarningSpec:
    severity_suggested: Severity
    description: str
    related_field: str | None


# Mapping from precursor code → display spec. Codes that callers emit but that
# are NOT in this catalog fall through unchanged via `to_warning_or_none` and
# are reported via a sentinel `description="<missing description>"` so the
# omission surfaces in CI rather than silently dropping a warning row.
WARNING_CATALOG: dict[str, WarningSpec] = {
    "annual_rate_inconsistent_with_monthly": WarningSpec(
        severity_suggested="yellow",
        description=(
            "La tasa mensual declarada no coincide con la tasa anual al capitalizar. "
            "Verificá el clausulado para asegurar el costo financiero real."
        ),
        related_field="annual_rate_pct",
    ),
    "annual_rate_not_expressed": WarningSpec(
        severity_suggested="red",
        description=(
            "El contrato no expresa la tasa de interés efectiva anual. "
            "Sin este dato no se puede comparar contra el mercado."
        ),
        related_field="annual_rate_pct",
    ),
    "monthly_payment_higher_than_theoretical": WarningSpec(
        severity_suggested="yellow",
        description=(
            "La cuota mensual difiere más de un 5% de la cuota amortizable " "teórica a la misma tasa y plazo."
        ),
        related_field="monthly_payment",
    ),
    "interest_calculation_base_unfavorable": WarningSpec(
        severity_suggested="red",
        description=(
            "Los intereses se calculan sobre el saldo total y no sobre el saldo "
            "pendiente. Verificá el texto contractual con un abogado."
        ),
        related_field="interest_calculation_base",
    ),
    "term_excessive": WarningSpec(
        severity_suggested="red",
        description=("El plazo de financiamiento excede el máximo legal aplicable al " "tipo de inmueble."),
        related_field="term_months",
    ),
    "down_payment_inconsistent": WarningSpec(
        severity_suggested="yellow",
        description=("El porcentaje y el monto de la prima no cuadran con el precio al " "contado."),
        related_field="down_payment",
    ),
    "total_cost_not_disclosed": WarningSpec(
        severity_suggested="red",
        description=("No se encuentra una cifra clara del costo total en el texto " "analizado."),
        related_field=None,
    ),
}


def to_warning_or_none(code: str) -> WarningSpec | None:
    """Return the catalog entry for `code` or `None` if the code is unknown."""

    return WARNING_CATALOG.get(code)


__all__ = ["WARNING_CATALOG", "Severity", "WarningSpec", "to_warning_or_none"]
