"""CS-132: monthly payment alignment ratio (RUBRICA_CONTRATO §5 B5).

Computes the asymmetric ratio between the contract's monthly installment and
the linear-amortization baseline `price_cash / term_months`. Ratios above 1
indicate that the contract front-loads cost relative to a straight-line
payment schedule (typical for amortized financing); ratios above the
`monthly_payment_ratio_excessive_min` benchmark are presumptive evidence of
predatory pricing per RUBRICA §5 B5.

Numeric policy (per plan): `float` for the ratio math, `Decimal` quantized to
0.0001 at the boundary for deterministic serialization.

Threshold parameters are taken from `economic_benchmarks.yaml`
(`monthly_payment_ratio_healthy_max`, `_high_max`, `_excessive_min`) and
passed in by the assembler (CS-135) rather than fetched here — keeps this
module pure and trivially testable.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.domain.payment_ratio import MonthlyRatioBand, RatioComputation


SKIP_REASON_INSUFFICIENT_INPUTS = "insufficient_inputs"
SKIP_REASON_ZERO_TERM = "zero_term"

# Storage / JSON-boundary precision. Mirrors `EconomicBenchmark.value_default`
# DecimalField(18, 4) and the CS-131 boundary policy.
_QUANTIZE = Decimal("0.0001")


def compute_monthly_ratio(
    extraction: AggregatedExtraction,
    *,
    healthy_max: Decimal,
    high_max: Decimal,
    excessive_min: Decimal,
) -> RatioComputation:
    """Resolve ratio + band from the extraction slots and benchmark thresholds.

    Args:
        extraction: aggregated F2 output. Reads `purchase_price_usd`,
            `term_months`, and `monthly_payment_usd` slots gated on
            `status == PRESENT`.
        healthy_max: `monthly_payment_ratio_healthy_max` from active YAML.
        high_max: `monthly_payment_ratio_high_max`.
        excessive_min: `monthly_payment_ratio_excessive_min`.

    Returns:
        `RatioComputation` with `ratio` and `baseline_monthly_linear`
        quantized to four decimal places, or a SKIPPED record with a
        machine-readable `skip_reason` when inputs are insufficient.
    """

    price = _slot_value(extraction.slots.get("purchase_price_usd"))
    term = _slot_value(extraction.slots.get("term_months"))
    monthly = _slot_value(extraction.slots.get("monthly_payment_usd"))

    if price is None or term is None or monthly is None:
        return _skipped(SKIP_REASON_INSUFFICIENT_INPUTS)
    if term == 0:
        return _skipped(SKIP_REASON_ZERO_TERM)
    if price <= 0:
        return _skipped(SKIP_REASON_INSUFFICIENT_INPUTS)

    baseline = price / term
    ratio = monthly / baseline

    return RatioComputation(
        ratio=_quantize(ratio),
        baseline_monthly_linear=_quantize(baseline),
        band=_classify(ratio, healthy_max, high_max, excessive_min),
        skip_reason=None,
    )


# ─── Internals ───────────────────────────────────────────────────────────────


def _slot_value(slot: EconomicSlot | None) -> float | None:
    if slot is None or slot.status != ExtractionStatus.PRESENT:
        return None
    value = slot.value
    if value is None or not isinstance(value, (int, float)):
        return None
    return float(value)


def _classify(
    ratio: float,
    healthy_max: Decimal,
    high_max: Decimal,
    excessive_min: Decimal,
) -> MonthlyRatioBand:
    """Assign a band per RUBRICA §14 thresholds.

    Inclusive at the lower bound: a ratio exactly equal to `healthy_max` is
    HEALTHY (the rubric §5 B5 narrative reads "ratio entre 1.0 y 1.2"
    inclusive). The `excessive_min` boundary is also inclusive (a 1.7 ratio
    is `EXCESSIVE`).
    """

    r = Decimal(str(ratio))
    if r <= healthy_max:
        return MonthlyRatioBand.HEALTHY
    if r <= high_max:
        return MonthlyRatioBand.ELEVATED
    if r < excessive_min:
        return MonthlyRatioBand.HIGH
    return MonthlyRatioBand.EXCESSIVE


def _quantize(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_QUANTIZE, rounding=ROUND_HALF_EVEN)


def _skipped(reason: str) -> RatioComputation:
    return RatioComputation(
        ratio=None,
        baseline_monthly_linear=None,
        band=MonthlyRatioBand.SKIPPED,
        skip_reason=reason,
    )


__all__ = [
    "SKIP_REASON_INSUFFICIENT_INPUTS",
    "SKIP_REASON_ZERO_TERM",
    "compute_monthly_ratio",
]
