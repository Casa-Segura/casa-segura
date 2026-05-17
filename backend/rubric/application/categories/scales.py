"""Deterministic ladders for the numeric criteria (B1, B2, B3, B4, B5, B8).

These are direct transcriptions of the per-criterion scoring tables in
RUBRICA_CONTRATO §5 and §9. They exist so the score ladder is owned by
*code*, not by an LLM-decided number — when the contract data is
available (EconomicSummary), the evaluator pins the score
deterministically. The LLM remains the qualitative path for criteria
without numeric tables (Categories A, C, D, E, F).

The ladders use **left-inclusive, right-exclusive** bins except where
the rubric is explicit otherwise (B2's top band is "> 19" so 19 is the
last value in the "severe" band; B1's 35 is the last "very high" value;
B5's 1.7 is "≥ 1.7").
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class LadderResult:
    """Outcome of a deterministic ladder lookup."""

    score: float
    band_label: str  # "favorable" / "high" / "very_high" / "severe" / "out_of_market" etc.


# ── B1 — Down payment as % of total price (§5 B1) ────────────────────────


def b1_down_payment_score(down_payment_pct: Decimal) -> LadderResult:
    """B1: down payment ≤10% = 10, then 8 / 5 / 2 / 0 ladder.

    Asymmetric penalty (RUBRICA_CONTRATO §1.1): values below the
    standard benchmark are favorable to the buyer and score 10.

    Thresholds per §5 B1:
        ≤10  → 10
        10-15 → 8
        15-20 → 5
        20-35 → 2
        >35  → 0
    """

    pct = Decimal(str(down_payment_pct))
    if pct <= Decimal("10"):
        return LadderResult(score=10.0, band_label="favorable")
    if pct <= Decimal("15"):
        return LadderResult(score=8.0, band_label="moderate")
    if pct <= Decimal("20"):
        return LadderResult(score=5.0, band_label="high")
    if pct <= Decimal("35"):
        return LadderResult(score=2.0, band_label="very_high")
    return LadderResult(score=0.0, band_label="fraud_pattern")


# ── B2 — Effective annual interest rate (§5 B2) ──────────────────────────


def b2_annual_rate_score(annual_rate_pct: Decimal) -> LadderResult:
    """B2: APR ≤9% = 10, then 9 / 7 / 5 / 2 / 0 per §5 B2.

    Thresholds:
        ≤9   → 10
        9-10 → 9
        10-11 → 7
        11-14 → 5
        14-19 → 2
        >19  → 0
    """

    rate = Decimal(str(annual_rate_pct))
    if rate <= Decimal("9"):
        return LadderResult(score=10.0, band_label="within_market")
    if rate <= Decimal("10"):
        return LadderResult(score=9.0, band_label="slightly_above")
    if rate <= Decimal("11"):
        return LadderResult(score=7.0, band_label="above")
    if rate <= Decimal("14"):
        return LadderResult(score=5.0, band_label="bad")
    if rate <= Decimal("19"):
        return LadderResult(score=2.0, band_label="severe")
    return LadderResult(score=0.0, band_label="out_of_market")


# ── B3 — Credit term in years (§5 B3) ────────────────────────────────────


def b3_term_score(term_years: Decimal) -> LadderResult:
    """B3: 5-20 yrs = 10, 20-25 = 7, 25-30 = 4, >30 or pathological = 0."""

    years = Decimal(str(term_years))
    if years <= Decimal("0"):
        return LadderResult(score=0.0, band_label="pathological")
    if Decimal("5") <= years <= Decimal("20"):
        return LadderResult(score=10.0, band_label="reasonable")
    if years <= Decimal("25"):
        return LadderResult(score=7.0, band_label="long")
    if years <= Decimal("30"):
        return LadderResult(score=4.0, band_label="ivu_max")
    return LadderResult(score=0.0, band_label="excessive")


# ── B4 — Total cost / cash price multiplier (§5 B4) ──────────────────────


def b4_total_cost_score(multiplier: Decimal) -> LadderResult:
    """B4: ≤1.5x = 10, then 8 / 6 / 3 / 0 per §5 B4."""

    m = Decimal(str(multiplier))
    if m <= Decimal("1.5"):
        return LadderResult(score=10.0, band_label="healthy")
    if m <= Decimal("1.8"):
        return LadderResult(score=8.0, band_label="moderate")
    if m <= Decimal("2.0"):
        return LadderResult(score=6.0, band_label="expensive")
    if m <= Decimal("2.5"):
        return LadderResult(score=3.0, band_label="very_expensive")
    return LadderResult(score=0.0, band_label="usurious")


# ── B5 — Monthly payment ratio (§5 B5) ───────────────────────────────────


def b5_monthly_ratio_score(ratio: Decimal) -> LadderResult:
    """B5 ratio = monthly_payment ÷ (total_price / term_months)."""

    r = Decimal(str(ratio))
    if r <= Decimal("0"):
        return LadderResult(score=0.0, band_label="invalid")
    if r <= Decimal("1.2"):
        return LadderResult(score=10.0, band_label="aligned")
    if r <= Decimal("1.4"):
        return LadderResult(score=7.0, band_label="elevated")
    if r < Decimal("1.7"):
        return LadderResult(score=4.0, band_label="high")
    return LadderResult(score=0.0, band_label="excessive")


# ── B8 — Prepayment fee % of balance (§5 B8) ─────────────────────────────


def b8_prepayment_score(fee_pct: Decimal | None, prohibited: bool = False) -> LadderResult:
    if prohibited or fee_pct is None:
        return LadderResult(score=0.0, band_label="prohibited")
    pct = Decimal(str(fee_pct))
    if pct <= Decimal("0"):
        return LadderResult(score=10.0, band_label="free")
    if pct <= Decimal("1"):
        return LadderResult(score=7.0, band_label="reasonable")
    if pct <= Decimal("3"):
        return LadderResult(score=4.0, band_label="moderate")
    return LadderResult(score=0.0, band_label="prohibitive")


__all__ = [
    "LadderResult",
    "b1_down_payment_score",
    "b2_annual_rate_score",
    "b3_term_score",
    "b4_total_cost_score",
    "b5_monthly_ratio_score",
    "b8_prepayment_score",
]
