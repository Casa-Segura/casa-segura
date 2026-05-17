"""CS-137: renormalization + partial-payload precursor detection.

CS-135's assembler already gates `derivation_status` on whether any
`fields_derived` slot is populated, so the `insufficient_data` envelope is
free of fabricated zeros. This module layers two additional precursors that
need cross-slot inspection:

1. **`down_payment_inconsistent`** — fires when both `down_payment_usd` and
   `down_payment_pct` are PRESENT and `|down_payment - price * pct| /
   price > 5%`. PRD_F5 US-02 wants the direct value retained, and a
   warning surfaced.
2. **`total_cost_not_disclosed`** — fires when the assembler could not
   compute `total_cost_paid` AND the contract had at least one financing
   slot. (Pure absence of financing data falls under
   `annual_rate_not_expressed`; this code adds the explicit "couldn't
   sum it up" signal.)

The renormalizer is pure (PRD_F5 BR-13) and stateless. The assembler folds
its precursors into the warning list before deduplication.
"""

from __future__ import annotations

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.domain.total_cost import TotalCostBundle

DOWN_PAYMENT_TOLERANCE = 0.05  # PRD_F5 BR-07-style 5% cross-check.

WARNING_DOWN_PAYMENT_INCONSISTENT = "down_payment_inconsistent"
WARNING_TOTAL_COST_NOT_DISCLOSED = "total_cost_not_disclosed"


def detect_precursors(extraction: AggregatedExtraction, bundle: TotalCostBundle) -> tuple[str, ...]:
    """Return additional warning precursor codes triggered by cross-slot checks."""

    precursors: list[str] = []

    price = _slot_value(extraction.slots.get("purchase_price_usd"))
    down = _slot_value(extraction.slots.get("down_payment_usd"))
    down_pct = _slot_value(extraction.slots.get("down_payment_pct"))
    if price is not None and down is not None and down_pct is not None and price > 0:
        inferred = price * down_pct
        # PRD_F5 BR-07 / US-02: tolerance is 5% of the price (proportional check).
        if abs(down - inferred) / price > DOWN_PAYMENT_TOLERANCE:
            precursors.append(WARNING_DOWN_PAYMENT_INCONSISTENT)

    monthly = _slot_value(extraction.slots.get("monthly_payment_usd"))
    term = _slot_value(extraction.slots.get("term_months"))
    has_financing_signal = monthly is not None or term is not None
    if has_financing_signal and bundle.total_cost_paid is None:
        precursors.append(WARNING_TOTAL_COST_NOT_DISCLOSED)

    return tuple(precursors)


# ─── Internals ───────────────────────────────────────────────────────────────


def _slot_value(slot: EconomicSlot | None) -> float | None:
    if slot is None or slot.status != ExtractionStatus.PRESENT:
        return None
    value = slot.value
    if value is None or not isinstance(value, (int, float)):
        return None
    return float(value)


__all__ = [
    "DOWN_PAYMENT_TOLERANCE",
    "WARNING_DOWN_PAYMENT_INCONSISTENT",
    "WARNING_TOTAL_COST_NOT_DISCLOSED",
    "detect_precursors",
]
