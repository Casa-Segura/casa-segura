"""CS-132: monthly payment alignment ratio coverage.

Test intent (Rule 9): `test_division_order_guard` pins the asymmetric B5
definition `monthly_payment / (price_cash / term_months)`. Swapping
numerator and denominator gives the reciprocal (~0.307 instead of ~3.25)
and the test fails loudly.

BVA from RUBRICA §14 default thresholds (1.2 / 1.4 / 1.7):
    * 1.199 → HEALTHY, 1.201 → ELEVATED  (healthy_max edge)
    * 1.399 → ELEVATED, 1.401 → HIGH      (high_max edge)
    * 1.699 → HIGH,    1.701 → EXCESSIVE  (excessive_min edge)
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.contract_type import ContractType
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.application.payment_ratio import (
    SKIP_REASON_INSUFFICIENT_INPUTS,
    SKIP_REASON_ZERO_TERM,
    compute_monthly_ratio,
)
from economics.domain.payment_ratio import MonthlyRatioBand

HEALTHY_MAX = Decimal("1.2")
HIGH_MAX = Decimal("1.4")
EXCESSIVE_MIN = Decimal("1.7")


def _slot(name: str, value: float | int | None, status: ExtractionStatus) -> EconomicSlot:
    return EconomicSlot(
        field_name=name,
        status=status,
        value=value,
        confidence=0.9,
        rationale=None,
    )


def _extraction(
    *,
    price: float | None,
    term: int | None,
    monthly: float | None,
    statuses: dict[str, ExtractionStatus] | None = None,
) -> AggregatedExtraction:
    statuses = statuses or {}
    slots: dict[str, EconomicSlot] = {}
    if price is not None:
        slots["purchase_price_usd"] = _slot(
            "purchase_price_usd",
            price,
            statuses.get("purchase_price_usd", ExtractionStatus.PRESENT),
        )
    if term is not None:
        slots["term_months"] = _slot("term_months", term, statuses.get("term_months", ExtractionStatus.PRESENT))
    if monthly is not None:
        slots["monthly_payment_usd"] = _slot(
            "monthly_payment_usd",
            monthly,
            statuses.get("monthly_payment_usd", ExtractionStatus.PRESENT),
        )
    return AggregatedExtraction(contract_type=ContractType.CVP, slots=slots)


# ─── Happy path / golden vector ──────────────────────────────────────────────


def test_golden_vector_from_ticket():
    """80_000 USD price, 240-month term, $1083.50 monthly → ratio 3.2505."""

    extraction = _extraction(price=80_000, term=240, monthly=1083.50)

    result = compute_monthly_ratio(
        extraction,
        healthy_max=HEALTHY_MAX,
        high_max=HIGH_MAX,
        excessive_min=EXCESSIVE_MIN,
    )

    assert result.skip_reason is None
    assert result.ratio == Decimal("3.2505")
    assert result.baseline_monthly_linear == Decimal("333.3333")  # 80000/240 = 333.33333..., quantized
    assert result.band == MonthlyRatioBand.EXCESSIVE


def test_division_order_guard():
    """Rule 9 — `compute_monthly_ratio` MUST be monthly / baseline, not the inverse."""

    extraction = _extraction(price=80_000, term=240, monthly=1083.50)

    result = compute_monthly_ratio(
        extraction,
        healthy_max=HEALTHY_MAX,
        high_max=HIGH_MAX,
        excessive_min=EXCESSIVE_MIN,
    )

    # The inverse `baseline / monthly` would be ~0.307. Asserting the value is
    # well above 1 anchors the asymmetric direction.
    assert result.ratio is not None
    assert result.ratio > Decimal("1.0"), "regression — division swapped: ratio collapsed below 1 (RUBRICA §5 B5)"


# ─── BVA at each rail edge ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("monthly", "expected_band"),
    [
        # healthy_max edge: 1.2 inclusive on the HEALTHY side.
        (1.199 * (80_000 / 240), MonthlyRatioBand.HEALTHY),
        (1.2 * (80_000 / 240), MonthlyRatioBand.HEALTHY),
        (1.201 * (80_000 / 240), MonthlyRatioBand.ELEVATED),
        # high_max edge: 1.4 inclusive on the ELEVATED side.
        (1.399 * (80_000 / 240), MonthlyRatioBand.ELEVATED),
        (1.4 * (80_000 / 240), MonthlyRatioBand.ELEVATED),
        (1.401 * (80_000 / 240), MonthlyRatioBand.HIGH),
        # excessive_min edge: 1.7 inclusive on the EXCESSIVE side.
        (1.699 * (80_000 / 240), MonthlyRatioBand.HIGH),
        (1.7 * (80_000 / 240), MonthlyRatioBand.EXCESSIVE),
        (1.701 * (80_000 / 240), MonthlyRatioBand.EXCESSIVE),
    ],
)
def test_band_classification_at_rails(monthly: float, expected_band: MonthlyRatioBand):
    extraction = _extraction(price=80_000, term=240, monthly=monthly)

    result = compute_monthly_ratio(
        extraction,
        healthy_max=HEALTHY_MAX,
        high_max=HIGH_MAX,
        excessive_min=EXCESSIVE_MIN,
    )

    assert result.band == expected_band


# ─── Skip paths ──────────────────────────────────────────────────────────────


def test_term_zero_skips_with_zero_term_reason():
    extraction = _extraction(price=80_000, term=0, monthly=1083.50)

    result = compute_monthly_ratio(
        extraction,
        healthy_max=HEALTHY_MAX,
        high_max=HIGH_MAX,
        excessive_min=EXCESSIVE_MIN,
    )

    assert result.band == MonthlyRatioBand.SKIPPED
    assert result.skip_reason == SKIP_REASON_ZERO_TERM
    assert result.ratio is None
    assert result.baseline_monthly_linear is None


@pytest.mark.parametrize(
    ("price", "term", "monthly"),
    [
        (None, 240, 1083.50),
        (80_000, None, 1083.50),
        (80_000, 240, None),
    ],
)
def test_any_missing_slot_skips(price, term, monthly):
    extraction = _extraction(price=price, term=term, monthly=monthly)

    result = compute_monthly_ratio(
        extraction,
        healthy_max=HEALTHY_MAX,
        high_max=HIGH_MAX,
        excessive_min=EXCESSIVE_MIN,
    )

    assert result.band == MonthlyRatioBand.SKIPPED
    assert result.skip_reason == SKIP_REASON_INSUFFICIENT_INPUTS


def test_non_present_slot_treated_as_missing():
    """PRD_F5 US-01: only `PRESENT` slots are consumed."""

    extraction = _extraction(
        price=80_000,
        term=240,
        monthly=1083.50,
        statuses={"monthly_payment_usd": ExtractionStatus.AMBIGUOUS},
    )

    result = compute_monthly_ratio(
        extraction,
        healthy_max=HEALTHY_MAX,
        high_max=HIGH_MAX,
        excessive_min=EXCESSIVE_MIN,
    )

    assert result.band == MonthlyRatioBand.SKIPPED
    assert result.skip_reason == SKIP_REASON_INSUFFICIENT_INPUTS


def test_zero_or_negative_price_skips():
    extraction = _extraction(price=0, term=240, monthly=1083.50)

    result = compute_monthly_ratio(
        extraction,
        healthy_max=HEALTHY_MAX,
        high_max=HIGH_MAX,
        excessive_min=EXCESSIVE_MIN,
    )

    assert result.band == MonthlyRatioBand.SKIPPED
    assert result.skip_reason == SKIP_REASON_INSUFFICIENT_INPUTS
