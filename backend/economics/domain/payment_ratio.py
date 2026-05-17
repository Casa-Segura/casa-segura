"""Monthly payment alignment ratio DTO + band enum — CS-132.

`RatioComputation` carries the result of comparing the contract's
`monthly_payment` against the linear baseline `price_cash / term_months`
plus its bucketed assessment band. The math itself lives in
`economics.application.payment_ratio`.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MonthlyRatioBand(StrEnum):
    """Closed set of `monthly_payment_ratio` assessment bands.

    Mirrors RUBRICA_CONTRATO §14 `monthly_payment.ratio_*` rails. The exact
    threshold values come from `economic_benchmarks.yaml`; this enum only
    enumerates the named bands so CS-134 / EPIC-06 can consume a discrete
    label.

    Bands (inclusive lower bound, exclusive upper bound):
        HEALTHY     — ratio ≤ ratio_healthy_max
        ELEVATED    — ratio_healthy_max < ratio ≤ ratio_high_max
        HIGH        — ratio_high_max < ratio < ratio_excessive_min
        EXCESSIVE   — ratio ≥ ratio_excessive_min
        SKIPPED     — denominator unusable; no band assigned
    """

    HEALTHY = "healthy"
    ELEVATED = "elevated"
    HIGH = "high"
    EXCESSIVE = "excessive"
    SKIPPED = "skipped"


class RatioComputation(BaseModel):
    """Output of the monthly-payment-ratio computation.

    Fields:
        ratio: `monthly_payment / (price_cash / term_months)`. None when
            inputs are insufficient (any of the three slots missing, or
            `term_months == 0`).
        baseline_monthly_linear: the denominator (`price_cash / term_months`).
            Echoed for the report / assembler so the storytelling layer
            can cite both numerator and baseline.
        band: bucketed assessment per `MonthlyRatioBand`. `SKIPPED` when
            ratio is None.
        skip_reason: short machine code explaining a SKIPPED result:
            * `insufficient_inputs` — one of the three slots was not PRESENT.
            * `zero_term` — `term_months` resolved to zero.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    ratio: Decimal | None = Field(default=None)
    baseline_monthly_linear: Decimal | None = Field(default=None)
    band: MonthlyRatioBand
    skip_reason: str | None = Field(default=None, max_length=64)


__all__ = ["MonthlyRatioBand", "RatioComputation"]
