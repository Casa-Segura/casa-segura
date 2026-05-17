"""CS-133: total cost paid, French amortization, and BR-07 coherence coverage.

Test intent (Rule 9): `test_french_amortization_formula_guard` pins the
denominator `(1+r)^n - 1` against the wrong `r * n` substitution. A
developer who replaces the geometric series with linear math sees this
test fail loudly (BR-06).

Golden vector reproduces a reference spreadsheet:
    L = 72_000 USD, annual = 0.09, term = 240 months
    r = 0.0075, (1+r)^240 ≈ 6.00915, denom ≈ 5.00915
    payment = 72_000 * 0.0075 * 6.00915 / 5.00915 ≈ 647.81
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.contract_type import ContractType
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.application.total_cost import (
    WARNING_MONTHLY_PAYMENT_HIGHER_THAN_THEORETICAL,
    WARNING_TERM_EXCESSIVE,
    compute_theoretical_monthly_payment,
    compute_total_cost,
)


def _slot(name: str, value: float | int | None, status: ExtractionStatus = ExtractionStatus.PRESENT) -> EconomicSlot:
    return EconomicSlot(field_name=name, status=status, value=value, confidence=0.9)


def _extraction(**slot_values: float | int | None) -> AggregatedExtraction:
    slots = {name: _slot(name, val) for name, val in slot_values.items() if val is not None}
    return AggregatedExtraction(contract_type=ContractType.CVP, slots=slots)


# ─── Theoretical monthly payment (pure helper) ───────────────────────────────


def test_french_amortization_golden_vector():
    payment = compute_theoretical_monthly_payment(
        financed_amount=72_000.0, annual_rate_pct=0.09, term_months=240
    )
    assert payment is not None
    assert payment == pytest.approx(647.81, abs=0.01)


def test_french_amortization_formula_guard():
    """Rule 9 — the wrong `r * n` denominator yields a wildly different value.

    `r*n = 0.0075 * 240 = 1.8`, so `payment = 72_000 * 0.0075 * 6.00915 / 1.8`
    would be ~1803, ~2.8x the correct ~647.81. PRD_F5 BR-06.
    """

    payment = compute_theoretical_monthly_payment(72_000.0, 0.09, 240)
    assert payment is not None
    assert payment < 1000, (
        "regression — amortization denominator collapsed to `r * n`; PRD_F5 BR-06"
    )


def test_zero_rate_yields_straight_line_payment():
    payment = compute_theoretical_monthly_payment(60_000.0, 0.0, 120)
    assert payment == pytest.approx(500.0)


def test_non_positive_inputs_return_none():
    assert compute_theoretical_monthly_payment(0, 0.09, 240) is None
    assert compute_theoretical_monthly_payment(72_000, 0.09, 0) is None
    assert compute_theoretical_monthly_payment(72_000, -0.01, 240) is None


# ─── compute_total_cost full happy path ──────────────────────────────────────


def test_total_cost_full_happy_path():
    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=8_000,
        financed_amount_usd=72_000,
        term_months=240,
        monthly_payment_usd=650.0,
    )

    bundle = compute_total_cost(extraction, annual_rate_pct=Decimal("0.09"))

    assert bundle.financed_amount_resolved == Decimal("72000.0000")
    assert bundle.monthly_payment_theoretical == Decimal("647.8027")
    # extracted monthly 650 vs theoretical 647.81 → coherent (BR-07).
    assert bundle.monthly_payment_coherent is True
    assert bundle.total_cost_paid == Decimal("164000.0000")  # 8000 + 650 * 240
    assert bundle.total_cost_vs_cash_multiplier == Decimal("2.0500")  # 164000 / 80000
    assert bundle.warning_precursors == ()


def test_total_cost_derives_financed_when_slot_missing():
    """BR-09: `financed = price - down` is allowed when the slot is silent."""

    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=8_000,
        term_months=240,
        monthly_payment_usd=650.0,
    )

    bundle = compute_total_cost(extraction, annual_rate_pct=Decimal("0.09"))

    assert bundle.financed_amount_resolved == Decimal("72000.0000")


def test_total_cost_returns_none_when_financed_cannot_be_resolved():
    """BR-09: no zero substitution. Without price OR down, financed is None."""

    extraction = _extraction(
        purchase_price_usd=80_000,
        term_months=240,
        monthly_payment_usd=650.0,
    )

    bundle = compute_total_cost(extraction, annual_rate_pct=Decimal("0.09"))

    assert bundle.financed_amount_resolved is None
    assert bundle.monthly_payment_theoretical is None
    assert bundle.monthly_payment_coherent is None


def test_total_cost_omits_down_payment_when_missing():
    """BR-09: missing down does not stop us from reporting `monthly * term` total."""

    extraction = _extraction(
        purchase_price_usd=80_000,
        financed_amount_usd=72_000,
        term_months=240,
        monthly_payment_usd=650.0,
    )

    bundle = compute_total_cost(extraction, annual_rate_pct=Decimal("0.09"))

    # 650 * 240 = 156_000 — no zero substitution for missing down_payment.
    assert bundle.total_cost_paid == Decimal("156000.0000")


# ─── BR-07 coherence boundaries ──────────────────────────────────────────────


def test_coherence_at_exact_tolerance_is_coherent():
    """`|extracted - theoretical| / theoretical == 0.05` is coherent (inclusive)."""

    theoretical = compute_theoretical_monthly_payment(72_000.0, 0.09, 240)
    assert theoretical is not None
    # Construct an extracted value 5% above theoretical.
    extracted = theoretical * 1.05

    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=8_000,
        financed_amount_usd=72_000,
        term_months=240,
        monthly_payment_usd=extracted,
    )

    bundle = compute_total_cost(extraction, annual_rate_pct=Decimal("0.09"))

    assert bundle.monthly_payment_coherent is True
    assert WARNING_MONTHLY_PAYMENT_HIGHER_THAN_THEORETICAL not in bundle.warning_precursors


def test_coherence_above_tolerance_breaches_with_warning():
    theoretical = compute_theoretical_monthly_payment(72_000.0, 0.09, 240)
    assert theoretical is not None
    # 5.01% above theoretical — breach.
    extracted = theoretical * 1.0501

    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=8_000,
        financed_amount_usd=72_000,
        term_months=240,
        monthly_payment_usd=extracted,
    )

    bundle = compute_total_cost(extraction, annual_rate_pct=Decimal("0.09"))

    assert bundle.monthly_payment_coherent is False
    assert WARNING_MONTHLY_PAYMENT_HIGHER_THAN_THEORETICAL in bundle.warning_precursors


def test_coherence_skipped_when_either_side_missing():
    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=8_000,
        financed_amount_usd=72_000,
        term_months=240,
        monthly_payment_usd=650.0,
    )

    # No annual rate → no theoretical → coherence undecidable.
    bundle = compute_total_cost(extraction, annual_rate_pct=None)

    assert bundle.monthly_payment_theoretical is None
    assert bundle.monthly_payment_coherent is None


# ─── Term excessive warning ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("term", "ivu_max", "expected_warning"),
    [
        (360, 360, False),  # equal — not excessive (inclusive cap)
        (361, 360, True),
        (300, 360, False),
    ],
)
def test_term_excessive_warning(term: int, ivu_max: int, expected_warning: bool):
    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=8_000,
        financed_amount_usd=72_000,
        term_months=term,
        monthly_payment_usd=650.0,
    )

    bundle = compute_total_cost(
        extraction, annual_rate_pct=Decimal("0.09"), ivu_max_term_months=ivu_max
    )

    if expected_warning:
        assert WARNING_TERM_EXCESSIVE in bundle.warning_precursors
    else:
        assert WARNING_TERM_EXCESSIVE not in bundle.warning_precursors


def test_term_excessive_silent_without_benchmark():
    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=8_000,
        financed_amount_usd=72_000,
        term_months=480,
        monthly_payment_usd=650.0,
    )

    bundle = compute_total_cost(extraction, annual_rate_pct=Decimal("0.09"))

    assert WARNING_TERM_EXCESSIVE not in bundle.warning_precursors
