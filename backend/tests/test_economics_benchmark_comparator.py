"""CS-134: benchmark comparator + overcost USD coverage.

Test intent (Rule 9):
    `test_below_market_never_synthesizes_overcost` pins the BR-02 asymmetric
    rule. If a developer accidentally inverts the sign or removes the
    `contract <= benchmark` guard, the test will fail because favorable
    contracts must NEVER emit an overcost row.

BVA at the assessment band edges (delta_pp = `(contract - bench) * 100`):
    -0.01 → below_market_favorable
     0.00 → within_market (BR-02 boundary is inclusive at zero)
     0.99 → within_market
     1.00 → above_market
     4.99 → above_market
     5.00 → well_above_market
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from classification.domain.contract_type import ContractType
from economics.application.benchmark_comparator import (
    RateBand,
    assess_delta,
    compare_rate,
    compute_overcost,
    select_segment,
)
from economics.domain.benchmark_comparison import BenchmarkSegment

BANK_BAND = RateBand(
    min_value=Decimal("0.07"),
    max_value=Decimal("0.09"),
    mid_value=Decimal("0.08"),
    mid_benchmark_key="bank_mortgage_rate_mid",
    mid_benchmark_source="RUBRICA §14 — Bank mortgage mid",
)
FSV_BAND = RateBand(
    min_value=Decimal("0.05"),
    max_value=Decimal("0.07"),
    mid_value=Decimal("0.06"),
    mid_benchmark_key="fsv_rate_mid",
    mid_benchmark_source="RUBRICA §14 — FSV mid",
)


# ─── select_segment ──────────────────────────────────────────────────────────


def test_select_segment_defaults_to_bank_for_purchase_types():
    assert select_segment(ContractType.CVP) == BenchmarkSegment.BANK_PURCHASE
    assert select_segment(ContractType.CVC) == BenchmarkSegment.BANK_PURCHASE
    assert select_segment(ContractType.APV) == BenchmarkSegment.BANK_PURCHASE


def test_select_segment_picks_fsv_for_fsv_contracts():
    assert select_segment(ContractType.FSV) == BenchmarkSegment.FSV


def test_select_segment_developer_direct_when_hint():
    assert select_segment(ContractType.CVP, has_developer_direct_hint=True) == BenchmarkSegment.DEVELOPER_DIRECT


# ─── BVA at assessment band edges ────────────────────────────────────────────


@pytest.mark.parametrize(
    ("delta_pp", "expected"),
    [
        (Decimal("-0.01"), "below_market_favorable"),
        (Decimal("0.00"), "within_market"),
        (Decimal("0.99"), "within_market"),
        (Decimal("1.00"), "above_market"),
        (Decimal("4.99"), "above_market"),
        (Decimal("5.00"), "well_above_market"),
    ],
)
def test_assess_delta_bands(delta_pp: Decimal, expected: str):
    assert assess_delta(delta_pp) == expected


# ─── compare_rate ────────────────────────────────────────────────────────────


def test_compare_rate_well_above_market_row():
    """Contract 18% vs bank mid 8% → delta 10pp → well_above_market."""

    comparison = compare_rate(
        contract_annual_pct=Decimal("0.18"),
        segment_band=BANK_BAND,
        segment=BenchmarkSegment.BANK_PURCHASE,
    )

    assert comparison.metric == "annual_rate"
    assert comparison.contract_value == Decimal("0.1800")
    assert comparison.benchmark_value == Decimal("0.0800")
    assert comparison.benchmark_key == "bank_mortgage_rate_mid"
    assert comparison.delta_pct_points == Decimal("10.0000")
    assert comparison.assessment == "well_above_market"


def test_compare_rate_favorable_when_below_benchmark():
    """Contract 7% vs bank mid 8% → delta -1pp → below_market_favorable."""

    comparison = compare_rate(
        contract_annual_pct=Decimal("0.07"),
        segment_band=BANK_BAND,
        segment=BenchmarkSegment.BANK_PURCHASE,
    )

    assert comparison.delta_pct_points == Decimal("-1.0000")
    assert comparison.assessment == "below_market_favorable"


# ─── compute_overcost — BR-02 / BR-11 / BR-09 paths ──────────────────────────


def test_below_market_never_synthesizes_overcost():
    """Rule 9 — BR-02 asymmetric: contract better than benchmark MUST yield None."""

    overcost = compute_overcost(
        contract_annual_pct=Decimal("0.07"),
        contract_term_months=240,
        contract_financed_amount=Decimal("72000"),
        contract_total_cost_paid=Decimal("100000"),
        segment_band=BANK_BAND,
        segment=BenchmarkSegment.BANK_PURCHASE,
        contract_down_payment=Decimal("8000"),
    )

    assert overcost is None, "BR-02 — below-market contracts must NEVER emit an overcost row"


def test_fsv_inside_band_skips_overcost():
    """BR-11 — FSV rates inside `[fsv_min, fsv_max]` are not compared against bank."""

    overcost = compute_overcost(
        contract_annual_pct=Decimal("0.065"),  # inside [0.05, 0.07]
        contract_term_months=240,
        contract_financed_amount=Decimal("72000"),
        contract_total_cost_paid=Decimal("160000"),
        segment_band=FSV_BAND,
        segment=BenchmarkSegment.FSV,
        contract_down_payment=Decimal("8000"),
    )

    assert overcost is None


def test_above_market_emits_overcost_with_explanation():
    """Contract 18% vs bank mid 8% over 240 months → meaningful USD overcost."""

    overcost = compute_overcost(
        contract_annual_pct=Decimal("0.18"),
        contract_term_months=240,
        contract_financed_amount=Decimal("72000"),
        contract_total_cost_paid=Decimal("268040"),
        segment_band=BANK_BAND,
        segment=BenchmarkSegment.BANK_PURCHASE,
        contract_down_payment=Decimal("8000"),
    )

    assert overcost is not None
    assert overcost.vs_benchmark_usd > Decimal("0")
    assert "tasa" in overcost.explanation.lower()
    assert overcost.what_changes_would_save  # non-empty


def test_missing_total_cost_returns_none():
    overcost = compute_overcost(
        contract_annual_pct=Decimal("0.18"),
        contract_term_months=240,
        contract_financed_amount=Decimal("72000"),
        contract_total_cost_paid=None,
        segment_band=BANK_BAND,
        segment=BenchmarkSegment.BANK_PURCHASE,
        contract_down_payment=Decimal("8000"),
    )

    assert overcost is None
