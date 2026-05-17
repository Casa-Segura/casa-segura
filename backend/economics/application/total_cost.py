"""CS-133: total cost paid, French amortization, and BR-07 coherence check.

Computes the derived figures that feed `EconomicSummary.fields_derived`:

* `monthly_payment_theoretical` via the standard French amortization
  formula `P = L * (r * (1+r)^n) / ((1+r)^n - 1)` where `r = annual/12`,
  `n = term_months`, `L = financed_amount` (PRD_F5 BR-06).
* `total_cost_paid = down_payment + monthly_payment * term_months`. Uses
  the EXTRACTED monthly so the multiplier reports the contract's actual
  cumulative outlay (BR-09 — no zero substitution; we never invent a
  monthly figure when the contract is silent).
* `total_cost_vs_cash_multiplier = total_cost_paid / price_cash`.
* `monthly_payment_coherent` — `|extracted - theoretical| / theoretical
  ≤ BR-07 tolerance (5%)`. Breach emits the
  `monthly_payment_higher_than_theoretical` warning precursor.

Numeric policy: `float` for the amort math, `Decimal` quantized to 0.0001
at the serialization boundary. The `r = 0` case short-circuits to
`financed / n` to avoid div-by-zero.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.domain.total_cost import TotalCostBundle


# PRD_F5 BR-07 — extracted vs theoretical coherence tolerance.
COHERENCE_TOLERANCE = 0.05

# Storage / JSON-boundary precision. Mirrors `EconomicBenchmark.value_default`
# DecimalField(18, 4) and CS-131 / CS-132 boundary policy.
_QUANTIZE = Decimal("0.0001")

# Warning precursor codes (subset of PRD_F5 US-06 taxonomy).
WARNING_MONTHLY_PAYMENT_HIGHER_THAN_THEORETICAL = "monthly_payment_higher_than_theoretical"
WARNING_TERM_EXCESSIVE = "term_excessive"


def compute_theoretical_monthly_payment(
    financed_amount: float, annual_rate_pct: float, term_months: int
) -> float | None:
    """French amortization payment under `(financed, annual, term)`.

    Returns `None` when any input is non-positive (the assembler treats a
    `None` result as `derivation_gap` per PRD_F5 BR-09). The `annual = 0`
    edge collapses to straight-line `financed / term`.
    """

    if financed_amount <= 0 or term_months <= 0 or annual_rate_pct < 0:
        return None
    if annual_rate_pct == 0:
        return financed_amount / term_months

    r = annual_rate_pct / 12
    # `(1 + r) ** n - 1` is the denominator that distinguishes French amort
    # from linear / interest-only schedules; the Rule 9 test pins this
    # against `r * n` (BR-06).
    factor = (1 + r) ** term_months
    return financed_amount * (r * factor) / (factor - 1)


def compute_total_cost(
    extraction: AggregatedExtraction,
    *,
    annual_rate_pct: Decimal | None,
    ivu_max_term_months: int | None = None,
) -> TotalCostBundle:
    """Build the `TotalCostBundle` from extraction slots + normalized rate.

    Args:
        extraction: aggregated F2 output. Reads `purchase_price_usd`,
            `down_payment_usd`, `financed_amount_usd`, `term_months`,
            `monthly_payment_usd`.
        annual_rate_pct: canonical annual rate from CS-131 (the assembler
            passes `RateNormalization.annual_rate_pct`). `None` when the
            normalizer could not produce a usable rate.
        ivu_max_term_months: optional benchmark `credit_term_ivu_max_months`
            value to drive the `term_excessive` warning precursor. If
            `None`, the warning is not emitted.
    """

    price = _slot_value(extraction.slots.get("purchase_price_usd"))
    down = _slot_value(extraction.slots.get("down_payment_usd"))
    financed_slot = _slot_value(extraction.slots.get("financed_amount_usd"))
    term = _slot_value(extraction.slots.get("term_months"))
    monthly = _slot_value(extraction.slots.get("monthly_payment_usd"))

    financed_resolved = _resolve_financed_amount(financed_slot, price, down)

    annual = float(annual_rate_pct) if annual_rate_pct is not None else None
    theoretical = (
        compute_theoretical_monthly_payment(financed_resolved, annual, int(term))
        if financed_resolved is not None and annual is not None and term is not None
        else None
    )

    total_paid: float | None
    if down is not None and monthly is not None and term is not None:
        total_paid = down + monthly * term
    elif monthly is not None and term is not None:
        # `down_payment` is silent: report the financed half only (BR-09 —
        # don't invent a down payment value). The assembler will surface
        # this as `partial` derivation status via CS-137.
        total_paid = monthly * term
    else:
        total_paid = None

    multiplier = (
        total_paid / price if (total_paid is not None and price is not None and price > 0) else None
    )

    coherent, coherence_warning = _check_coherence(monthly, theoretical)

    warnings: list[str] = []
    if coherence_warning is not None:
        warnings.append(coherence_warning)
    if (
        ivu_max_term_months is not None
        and term is not None
        and term > ivu_max_term_months
    ):
        warnings.append(WARNING_TERM_EXCESSIVE)

    return TotalCostBundle(
        financed_amount_resolved=_quantize(financed_resolved) if financed_resolved is not None else None,
        monthly_payment_theoretical=_quantize(theoretical) if theoretical is not None else None,
        total_cost_paid=_quantize(total_paid) if total_paid is not None else None,
        total_cost_vs_cash_multiplier=_quantize(multiplier) if multiplier is not None else None,
        monthly_payment_coherent=coherent,
        warning_precursors=tuple(warnings),
    )


# ─── Internals ───────────────────────────────────────────────────────────────


def _slot_value(slot: EconomicSlot | None) -> float | None:
    if slot is None or slot.status != ExtractionStatus.PRESENT:
        return None
    value = slot.value
    if value is None or not isinstance(value, (int, float)):
        return None
    return float(value)


def _resolve_financed_amount(
    financed_slot: float | None, price: float | None, down: float | None
) -> float | None:
    """Echo extracted `financed_amount` when present; else derive `price - down`.

    BR-09 forbids silently substituting zero. If neither path is usable the
    function returns `None`; the assembler will mark downstream derivations
    as `derivation_gap`.
    """

    if financed_slot is not None and financed_slot > 0:
        return financed_slot
    if price is not None and down is not None:
        derived = price - down
        if derived > 0:
            return derived
    return None


def _check_coherence(
    monthly_extracted: float | None, monthly_theoretical: float | None
) -> tuple[bool | None, str | None]:
    """Return `(coherent_flag, optional_warning_precursor)`.

    PRD_F5 BR-07: coherence is satisfied when the relative gap is `≤ 5%`
    of the theoretical figure. The 5.0% mark is inclusive on the
    coherent side; 5.01% breaches.
    """

    if monthly_extracted is None or monthly_theoretical is None or monthly_theoretical <= 0:
        return None, None
    relative_gap = abs(monthly_extracted - monthly_theoretical) / monthly_theoretical
    # `1e-9` slack so the inclusive `<=` boundary survives normal float noise
    # (e.g. `theoretical * 1.05 / theoretical` can land at `0.0500000000007`).
    if relative_gap <= COHERENCE_TOLERANCE + 1e-9:
        return True, None
    return False, WARNING_MONTHLY_PAYMENT_HIGHER_THAN_THEORETICAL


def _quantize(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_QUANTIZE, rounding=ROUND_HALF_EVEN)


__all__ = [
    "COHERENCE_TOLERANCE",
    "WARNING_MONTHLY_PAYMENT_HIGHER_THAN_THEORETICAL",
    "WARNING_TERM_EXCESSIVE",
    "compute_theoretical_monthly_payment",
    "compute_total_cost",
]
