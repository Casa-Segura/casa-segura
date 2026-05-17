"""Art. 2 LAF leasing indicator set (CS-111).

This module owns the **structural indicator schema** the leasing
reclassification detector populates after CS-110 has assigned an
initial contract type. The indicators come from
``PRD_F2_CLASIFICACION`` §8.4 / US-03, which in turn paraphrases
Art. 2 of the Ley de Arrendamiento Financiero (LAF) of El Salvador
(see ``RUBRICA_CONTRATO`` §3).

Indicator set (canonical, **six**, ordered as in PRD §8.4)
----------------------------------------------------------
1. ``mandatory_term`` — plazo de cumplimiento forzoso: early
   cancellation requires paying the full outstanding balance.
2. ``predefined_purchase_option`` — opción de compra a precio
   predefinido at the end of the term (often symbolic, e.g. USD 100).
3. ``ownership_retained`` — la propiedad permanece en el "vendedor"
   hasta el ejercicio de la opción.
4. ``taxes_to_buyer`` — todos los tributos, tasas, multas e
   impuestos sobre el bien recaen en el "comprador".
5. ``risks_to_buyer`` — todos los riesgos (asegurables y no
   asegurables) recaen en el "comprador".
6. ``payments_as_rent`` — los pagos se denominan ``canon`` en lugar
   de cuota de precio.

The set is **closed**: the detector emits exactly these six booleans.
Adding or removing an indicator changes the legal-product hinge
(threshold of 4-of-6) and MUST go through a PRD revision per BR-03.

Threshold policy
----------------
``is_leasing(threshold: int = 4) -> bool`` returns ``True`` iff at
least ``threshold`` indicators were detected. The default is **4**,
which matches PRD F2 §10 Q1 / BR-03 — "Reclassification to leasing
requires at least 4 of the 6 Art. 2 LAF indicators". The numeric
cutoff is the legal-product hinge; downstream callers MUST go through
this method rather than re-implementing the comparison so a PRD
threshold change is a one-line edit.

DDD note
--------
Domain layer only. No ``django.*``, ``httpx``, ``requests``, or
``shared.llm.*`` imports — pydantic v2 is the only third-party
dependency, in line with the rest of ``classification/domain``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, computed_field

# Source-of-truth constants. Re-exported so the detector / orchestrator
# never hard-code the numbers; flipping the legal-product hinge here
# updates every caller.
LAF_INDICATOR_COUNT: int = 6
"""Total number of Art. 2 LAF indicators in the canonical set (PRD §8.4)."""

DEFAULT_RECLASSIFICATION_THRESHOLD: int = 4
"""Default minimum count to recommend reclassification to LEA (PRD BR-03)."""


class LeasingIndicators(BaseModel):
    """Six boolean flags from Art. 2 LAF (PRD F2 §8.4 / US-03).

    Each field is ``True`` when the LLM detected the indicator in the
    contract text. Evidence quotes are intentionally **not** stored
    here — they live on ``LeasingReclassificationResult.reasoning`` or
    on the future ``reclassification_indicators`` JSONB column (PRD
    US-03) so this domain shape stays cheap to log and compare.

    Use the ``total_indicators_found`` computed property and the
    ``is_leasing(threshold=...)`` helper instead of summing the
    booleans manually — that keeps the legal-product hinge under
    central control (CS-111 test intent: Rule 9).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mandatory_term: bool = Field(
        default=False,
        description=(
            "Indicador 1 (Art. 2 LAF): plazo de cumplimiento forzoso — "
            "la cancelación anticipada exige pagar el saldo total."
        ),
    )
    predefined_purchase_option: bool = Field(
        default=False,
        description=(
            "Indicador 2 (Art. 2 LAF): opción de compra a precio "
            "predefinido al final del plazo (con frecuencia simbólico)."
        ),
    )
    ownership_retained: bool = Field(
        default=False,
        description=(
            "Indicador 3 (Art. 2 LAF): la propiedad del bien se mantiene "
            "en el vendedor hasta el ejercicio de la opción de compra."
        ),
    )
    taxes_to_buyer: bool = Field(
        default=False,
        description=(
            "Indicador 4 (Art. 2 LAF): tributos, tasas, multas e " "impuestos sobre el bien recaen en el comprador."
        ),
    )
    risks_to_buyer: bool = Field(
        default=False,
        description=("Indicador 5 (Art. 2 LAF): riesgos asegurables y no " "asegurables recaen en el comprador."),
    )
    payments_as_rent: bool = Field(
        default=False,
        description=("Indicador 6 (Art. 2 LAF): los pagos se denominan canon en " "lugar de cuota de precio."),
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_indicators_found(self) -> int:
        """Count of indicators flagged as detected (0..6)."""
        return sum(
            (
                self.mandatory_term,
                self.predefined_purchase_option,
                self.ownership_retained,
                self.taxes_to_buyer,
                self.risks_to_buyer,
                self.payments_as_rent,
            )
        )

    def is_leasing(self, threshold: int = DEFAULT_RECLASSIFICATION_THRESHOLD) -> bool:
        """Return True iff at least ``threshold`` indicators were detected.

        ``threshold`` defaults to PRD BR-03's ``4`` (4-of-6). Callers
        such as the orchestrator (CS-112+) MUST use this helper rather
        than ``total_indicators_found >= n`` so the threshold lives in
        a single place — see ``DEFAULT_RECLASSIFICATION_THRESHOLD``.

        Raises ``ValueError`` if ``threshold`` is outside ``[0, 6]``
        to surface configuration mistakes (e.g. an env var set to ``7``)
        loudly rather than silently never reclassifying.
        """
        if not (0 <= threshold <= LAF_INDICATOR_COUNT):
            raise ValueError(f"threshold must be in [0, {LAF_INDICATOR_COUNT}]; got {threshold!r}")
        return self.total_indicators_found >= threshold


__all__ = [
    "DEFAULT_RECLASSIFICATION_THRESHOLD",
    "LAF_INDICATOR_COUNT",
    "LeasingIndicators",
]
