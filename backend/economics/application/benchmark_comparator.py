"""CS-134: per-metric benchmark comparisons + USD overcost computation.

This module is deliberately pure: it accepts already-extracted thresholds
and the normalized rate as inputs and returns a tuple of `BenchmarkComparison`
rows plus an `Overcost | None`. The active-catalog lookup is the assembler's
(CS-135) responsibility.

Assessment bands (per `docs/analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md`,
collapsing PRD_F5 US-04's 5-bucket scale to the persisted DOMAIN_MODEL §5.6
4-bucket enum already present in `economics/domain/enums.py`):

    delta_pp < 0          → below_market_favorable (BR-02 asymmetric rule)
    delta_pp ∈ [0, 1)     → within_market
    delta_pp ∈ [1, 5)     → above_market
    delta_pp ≥ 5          → well_above_market

The substitution rule for overcost (PRD_F5 US-05):
    - Bank-segment contract with `annual > bank_mortgage_rate_max` → swap
      to `bank_mortgage_rate_mid` and re-amortize at the same term + financed.
    - FSV contract inside `[fsv_rate_min, fsv_rate_max]` → no overcost
      computed (BR-11).
    - Below-market rate → `overcost = None` (BR-02 — never punish favorable).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from classification.domain.contract_type import ContractType
from economics.application.total_cost import compute_theoretical_monthly_payment
from economics.domain.benchmark_comparison import (
    BenchmarkComparison,
    BenchmarkSegment,
    Overcost,
)
from economics.domain.enums import BenchmarkAssessment

_QUANTIZE = Decimal("0.0001")
_USD_QUANTIZE = Decimal("0.01")

# Band edges expressed in percentage points (delta = contract_pct - benchmark_pct, * 100).
BAND_WITHIN_MAX_PP = Decimal("1.0")
BAND_ABOVE_MAX_PP = Decimal("5.0")


@dataclass(frozen=True)
class RateBand:
    """One segment's interest-rate band, sourced from the active YAML."""

    min_value: Decimal
    max_value: Decimal
    mid_value: Decimal
    mid_benchmark_key: str
    mid_benchmark_source: str


def select_segment(contract_type: ContractType, has_developer_direct_hint: bool = False) -> BenchmarkSegment:
    """Pick which rate band applies per BR-10 / BR-11.

    FSV uses its own band; CVC/CVP/APV default to the bank band unless the
    caller explicitly flags developer-direct financing (CS-135 will derive
    that flag from the contract's classification metadata once available).
    """

    if contract_type == ContractType.FSV:
        return BenchmarkSegment.FSV
    if has_developer_direct_hint:
        return BenchmarkSegment.DEVELOPER_DIRECT
    return BenchmarkSegment.BANK_PURCHASE


def assess_delta(delta_pp: Decimal) -> str:
    """Map a percentage-point delta to a DOMAIN_MODEL §5.6 assessment value."""

    if delta_pp < Decimal("0"):
        return BenchmarkAssessment.BELOW_MARKET_FAVORABLE.value
    if delta_pp < BAND_WITHIN_MAX_PP:
        return BenchmarkAssessment.WITHIN_MARKET.value
    if delta_pp < BAND_ABOVE_MAX_PP:
        return BenchmarkAssessment.ABOVE_MARKET.value
    return BenchmarkAssessment.WELL_ABOVE_MARKET.value


def compare_rate(
    *,
    contract_annual_pct: Decimal,
    segment_band: RateBand,
    segment: BenchmarkSegment,
) -> BenchmarkComparison:
    """Build the annual-rate `BenchmarkComparison` row.

    BR-11 — FSV: when the contract rate sits inside `[fsv_min, fsv_max]`, the
    delta is computed against the FSV mid; bank ladder is NOT consulted.
    """

    delta_pp = (contract_annual_pct - segment_band.mid_value) * Decimal("100")
    delta_pp_q = delta_pp.quantize(_QUANTIZE, rounding=ROUND_HALF_EVEN)

    # BR-02 asymmetric: even below-market values produce a row so the
    # report can cite the favorable comparison; the row's assessment will
    # be `below_market_favorable` and overcost stays None upstream.
    return BenchmarkComparison(
        metric="annual_rate",
        metric_label=_metric_label_for_segment(segment),
        contract_value=contract_annual_pct.quantize(_QUANTIZE, rounding=ROUND_HALF_EVEN),
        benchmark_value=segment_band.mid_value.quantize(_QUANTIZE, rounding=ROUND_HALF_EVEN),
        benchmark_key=segment_band.mid_benchmark_key,
        benchmark_source=segment_band.mid_benchmark_source,
        delta_pct_points=delta_pp_q,
        assessment=assess_delta(delta_pp_q),
    )


def compute_overcost(
    *,
    contract_annual_pct: Decimal,
    contract_term_months: int,
    contract_financed_amount: Decimal,
    contract_total_cost_paid: Decimal | None,
    segment_band: RateBand,
    segment: BenchmarkSegment,
    contract_down_payment: Decimal | None,
) -> Overcost | None:
    """Re-amortize at the benchmark mid rate and return the USD difference.

    Returns `None` when:
        - the contract rate sits at or below the benchmark mid (BR-02);
        - the FSV contract rate is inside its band (BR-11);
        - any of the amortization inputs is missing (BR-09 — no zero subs).
        - `contract_total_cost_paid` is None (we cannot compare without it).
    """

    if contract_total_cost_paid is None:
        return None

    # BR-11: FSV inside its own band → skip.
    if segment == BenchmarkSegment.FSV and (segment_band.min_value <= contract_annual_pct <= segment_band.max_value):
        return None

    # BR-02 asymmetric: favorable contracts never produce an overcost.
    if contract_annual_pct <= segment_band.mid_value:
        return None

    benchmark_monthly = compute_theoretical_monthly_payment(
        float(contract_financed_amount),
        float(segment_band.mid_value),
        contract_term_months,
    )
    if benchmark_monthly is None:
        return None

    down = float(contract_down_payment) if contract_down_payment is not None else 0.0
    benchmark_total = down + benchmark_monthly * contract_term_months
    overcost_value = float(contract_total_cost_paid) - benchmark_total
    if overcost_value <= 0:
        return None

    explanation = _build_overcost_explanation(
        contract_pct=contract_annual_pct,
        benchmark_pct=segment_band.mid_value,
        contract_total=contract_total_cost_paid,
        benchmark_total=Decimal(str(benchmark_total)),
    )
    what_changes = (
        f"Negociá bajar la tasa anual del {_pct(contract_annual_pct)} al "
        f"rango cercano al {_pct(segment_band.mid_value)} (referencia "
        f"{_segment_label(segment)} de mercado).",
    )

    return Overcost(
        vs_benchmark_usd=Decimal(str(overcost_value)).quantize(_USD_QUANTIZE, rounding=ROUND_HALF_EVEN),
        explanation=explanation,
        what_changes_would_save=what_changes,
    )


# ─── Internals ───────────────────────────────────────────────────────────────


def _metric_label_for_segment(segment: BenchmarkSegment) -> str:
    if segment == BenchmarkSegment.FSV:
        return "Tasa efectiva anual vs banda FSV"
    if segment == BenchmarkSegment.DEVELOPER_DIRECT:
        return "Tasa efectiva anual vs financiamiento directo"
    return "Tasa efectiva anual vs hipoteca bancaria"


def _segment_label(segment: BenchmarkSegment) -> str:
    if segment == BenchmarkSegment.FSV:
        return "FSV"
    if segment == BenchmarkSegment.DEVELOPER_DIRECT:
        return "desarrollador directo"
    return "bancaria"


def _pct(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)}%"


def _build_overcost_explanation(
    *,
    contract_pct: Decimal,
    benchmark_pct: Decimal,
    contract_total: Decimal,
    benchmark_total: Decimal,
) -> str:
    contract_total_q = contract_total.quantize(_USD_QUANTIZE, rounding=ROUND_HALF_EVEN)
    benchmark_total_q = benchmark_total.quantize(_USD_QUANTIZE, rounding=ROUND_HALF_EVEN)
    return (
        f"Si la tasa fuera del {_pct(benchmark_pct)} en lugar del "
        f"{_pct(contract_pct)}, pagarías {benchmark_total_q} USD en total. "
        f"Con el contrato indicado el costo nominal acumulado es "
        f"{contract_total_q} USD."
    )


__all__ = [
    "BAND_ABOVE_MAX_PP",
    "BAND_WITHIN_MAX_PP",
    "RateBand",
    "assess_delta",
    "compare_rate",
    "compute_overcost",
    "select_segment",
]
