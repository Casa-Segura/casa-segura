"""Total-cost derivation bundle — CS-133.

Carries everything CS-135 needs to populate `EconomicSummary.fields_derived`
plus the coherence verdict between extracted vs theoretical monthly payment.
The amortization math itself lives in `economics.application.total_cost`.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TotalCostBundle(BaseModel):
    """Derived total-cost figures for one contract.

    Fields mirror PRD_F5 §5 `fields_derived` keys:
        financed_amount_resolved: amount carried in the amortization,
            either echoed from the extracted slot or derived as
            `price_cash - down_payment` per PRD_F5 BR-09 honesty rules
            (NEVER substituted with a zero). None when no path was usable.
        monthly_payment_theoretical: French-amortization theoretical
            monthly installment under `(annual_rate_pct, term_months,
            financed_amount_resolved)`. None when any input is missing.
        total_cost_paid: `down_payment + monthly_payment * term_months`.
            Uses the EXTRACTED monthly payment, not the theoretical one
            (BR-09 — we report the contract's actual cumulative outlay).
        total_cost_vs_cash_multiplier: `total_cost_paid / price_cash`.
        monthly_payment_coherent: `True` if `|extracted - theoretical|
            / theoretical ≤ BR-07 tolerance (5%)`. `None` if either side
            is missing so the assembler can suppress the field rather
            than emit a misleading boolean.
        warning_precursors: F5 US-06 codes triggered by the coherence
            check. Currently:
              - `monthly_payment_higher_than_theoretical` (BR-07 breach).
              - `term_excessive` (`term_months > credit_term_ivu_max_months`).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    financed_amount_resolved: Decimal | None = Field(default=None)
    monthly_payment_theoretical: Decimal | None = Field(default=None)
    total_cost_paid: Decimal | None = Field(default=None)
    total_cost_vs_cash_multiplier: Decimal | None = Field(default=None)
    monthly_payment_coherent: bool | None = Field(default=None)
    warning_precursors: tuple[str, ...] = Field(default=())


__all__ = ["TotalCostBundle"]
