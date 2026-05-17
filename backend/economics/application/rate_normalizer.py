"""CS-131: deterministic effective-annual-rate normalization.

Maps the `interest_rate_pct` (annual) and `monthly_rate_pct` slots from
`AggregatedExtraction` into a single canonical `annual_rate_pct` in `[0, 1]`,
applying PRD_F5 rules:

* BR-05: monthly → annual conversion is **compound**, `(1+m)^12 - 1`. Never
  linear `12*m`.
* US-01: `annual_rate_pct` must lie in `[0, 1]`; values outside this window
  are marked `INVALID` and not consumed downstream.
* BR-13: pure deterministic logic; no LLM call.

Numeric policy (per plan): `float` for internal `(1+m)**12` math, `Decimal`
serialization at the boundary (`Decimal(str(value)).quantize(0.0001)`). The
quantize step keeps determinism across machines and matches the storage
precision of `EconomicBenchmark.value_default` (DecimalField 18,4).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.domain.rate_normalization import RateNormalization


# PRD_F5 US-01 — annual rate stored as decimal in [0, 1] (0% to 100%).
RATE_MIN = 0.0
RATE_MAX = 1.0

# Cross-source consistency tolerance when both `interest_rate_pct` and
# `monthly_rate_pct` are PRESENT. Aligns with PRD_F5 BR-07's 5% coherence
# window (here applied to the annual-equivalent comparison, not the cross-
# field amortization check that BR-07 targets).
INCONSISTENCY_TOLERANCE = 0.05

# Storage / JSON-boundary precision. Mirrors `EconomicBenchmark` DecimalField.
_QUANTIZE = Decimal("0.0001")

# Warning precursor codes (subset of PRD_F5 US-06 taxonomy emitted by F5 itself).
WARNING_ANNUAL_INCONSISTENT_WITH_MONTHLY = "annual_rate_inconsistent_with_monthly"
WARNING_ANNUAL_NOT_EXPRESSED = "annual_rate_not_expressed"


def normalize_annual_rate(extraction: AggregatedExtraction) -> RateNormalization:
    """Resolve the canonical annual rate from the extraction slots.

    Resolution order:
        1. Annual slot (`interest_rate_pct`) present and in range → use it.
           If a monthly slot is also present and the compound conversion
           differs by more than `INCONSISTENCY_TOLERANCE`, emit the
           `annual_rate_inconsistent_with_monthly` warning precursor (but
           still prefer the explicit annual figure per PRD_F2 BR-08).
        2. Monthly slot (`monthly_rate_pct`) present → compute `(1+m)^12 - 1`
           per BR-05. If the result falls outside `[0, 1]`, mark INVALID.
        3. Neither usable → `NOT_PRESENT` + `annual_rate_not_expressed`.
    """

    annual_slot = extraction.slots.get("interest_rate_pct")
    monthly_slot = extraction.slots.get("monthly_rate_pct")

    annual_value = _slot_value(annual_slot)
    monthly_value = _slot_value(monthly_slot)

    if annual_value is not None:
        return _normalize_from_annual(annual_value, monthly_value)
    if monthly_value is not None:
        return _normalize_from_monthly(monthly_value)
    return RateNormalization(
        annual_rate_pct=None,
        status=ExtractionStatus.NOT_PRESENT,
        derivation_note="not_expressed",
        warning_precursors=(WARNING_ANNUAL_NOT_EXPRESSED,),
    )


# ─── Internals ───────────────────────────────────────────────────────────────


def _slot_value(slot: EconomicSlot | None) -> float | None:
    """Return the numeric value of a PRESENT slot or None.

    Per PRD_F5 US-01: slots with status != PRESENT must NOT be consumed for
    computation. The `EconomicSlot.value` field may still carry a diagnostic
    payload (the rejected raw value) when status is INVALID / AMBIGUOUS, but
    callers must gate on status.
    """

    if slot is None or slot.status != ExtractionStatus.PRESENT:
        return None
    value = slot.value
    if value is None or not isinstance(value, (int, float)):
        return None
    return float(value)


def _normalize_from_annual(
    annual: float, monthly: float | None
) -> RateNormalization:
    if not _in_range(annual):
        return RateNormalization(
            annual_rate_pct=None,
            status=ExtractionStatus.INVALID,
            derivation_note="invalid_annual_out_of_range",
            warning_precursors=(),
        )

    warnings: tuple[str, ...] = ()
    if monthly is not None:
        if _in_range(monthly):
            converted = _compound(monthly)
            # Avoid div-by-zero when both rates are 0.
            denom = annual if annual > 0 else 1.0
            if abs(converted - annual) / denom > INCONSISTENCY_TOLERANCE:
                warnings = (WARNING_ANNUAL_INCONSISTENT_WITH_MONTHLY,)
        # If monthly is out of range we silently ignore it — the annual
        # was usable, no need to escalate two errors. The monthly slot
        # will be carried as INVALID on the EconomicSummary by CS-135.

    return RateNormalization(
        annual_rate_pct=_quantize(annual),
        status=ExtractionStatus.PRESENT,
        derivation_note="extracted_annual",
        warning_precursors=warnings,
    )


def _normalize_from_monthly(monthly: float) -> RateNormalization:
    if not _in_range(monthly):
        return RateNormalization(
            annual_rate_pct=None,
            status=ExtractionStatus.INVALID,
            derivation_note="invalid_monthly_out_of_range",
            warning_precursors=(),
        )
    converted = _compound(monthly)
    if not _in_range(converted):
        # Mathematically `(1+m)^12 - 1 > 1` requires `m > ~0.0595`. The
        # monthly was in [0,1] but the resulting annual exceeded the
        # PRD_F5 US-01 range — still INVALID, with a specific note so the
        # assembler can surface it.
        return RateNormalization(
            annual_rate_pct=None,
            status=ExtractionStatus.INVALID,
            derivation_note="invalid_compound_overflow",
            warning_precursors=(),
        )
    return RateNormalization(
        annual_rate_pct=_quantize(converted),
        status=ExtractionStatus.PRESENT,
        derivation_note="converted_from_monthly_compound",
        warning_precursors=(),
    )


def _compound(monthly: float) -> float:
    """`annual = (1 + monthly)^12 - 1` per PRD_F5 BR-05. NEVER `12 * monthly`."""

    return (1.0 + monthly) ** 12 - 1.0


def _in_range(value: float) -> bool:
    return RATE_MIN <= value <= RATE_MAX


def _quantize(value: float) -> Decimal:
    """Convert a float to fixed-precision Decimal for deterministic serialization.

    Uses `ROUND_HALF_EVEN` (banker's rounding) so cross-machine output is byte-
    equal even when the float carries `2.20...001`-style trailing noise.
    """

    return Decimal(str(value)).quantize(_QUANTIZE, rounding=ROUND_HALF_EVEN)


__all__ = [
    "INCONSISTENCY_TOLERANCE",
    "RATE_MAX",
    "RATE_MIN",
    "WARNING_ANNUAL_INCONSISTENT_WITH_MONTHLY",
    "WARNING_ANNUAL_NOT_EXPRESSED",
    "normalize_annual_rate",
]
