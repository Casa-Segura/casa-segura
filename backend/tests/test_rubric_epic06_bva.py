"""EPIC-06 BVA + property coverage — CS-167..CS-171."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import HealthCheck, assume, given, settings, strategies as st

from rubric.application.categories import category_a, category_b, category_c, category_d, category_e
from rubric.application.categories.scales import (
    b1_down_payment_score,
    b2_annual_rate_score,
    b3_term_score,
    b4_total_cost_score,
)
from rubric.application.services.asymmetric_penalty import (
    ClampOutcome,
    b1_inputs,
    b2_inputs,
    b3_inputs,
    b4_inputs,
    clamp_score,
)
from rubric.application.services.criterion_evaluator import CriterionSpec, EvaluationContext
from rubric.application.services.score_calculator import aggregate_total, assign_band, banker_round_score_total
from rubric.domain.band import Band, OverrideCode
from rubric.domain.entities import CriterionEvaluation

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "overrides"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def _spec(
    criterion_id: str,
    category: str,
    *,
    weight: float = 25.0,
    worst_unverified: float = 4.0,
    applicable_types: tuple[str, ...] = ("CVP", "CVC", "APV"),
) -> CriterionSpec:
    return CriterionSpec(
        criterion_id=criterion_id,
        category=category,  # type: ignore[arg-type]
        weight_in_category=weight,
        applicable_types=applicable_types,
        legal_anchor=(),
        override_code=None,
        evaluation_prompt="-",
        scoring_scale={},
        worst_case_when_unverifiable=worst_unverified,
    )


def _run(coro: Awaitable[CriterionEvaluation]) -> CriterionEvaluation:
    return asyncio.run(coro)


def _ctx(*, text: str, contract_type: str = "CVP", **kwargs: object) -> EvaluationContext:
    return EvaluationContext(
        analysis_id="test",
        contract_text=text,
        contract_type=contract_type,
        **kwargs,
    )


# ── CS-167 — band boundaries ─────────────────────────────────────────────


@pytest.mark.parametrize(
    ("total", "expected"),
    [
        (Decimal("0.0"), Band.RED),
        (Decimal("4.9"), Band.RED),
        (Decimal("5.0"), Band.YELLOW),
        (Decimal("7.9"), Band.YELLOW),
        (Decimal("8.0"), Band.GREEN),
        (Decimal("10.0"), Band.GREEN),
    ],
)
def test_cs167_assign_band_table(total: Decimal, expected: Band) -> None:
    assert assign_band(total) is expected


@pytest.mark.parametrize(
    ("pre", "rounded_expected", "band_expected"),
    [
        (Decimal("4.949"), Decimal("4.9"), Band.RED),
        (Decimal("4.950"), Decimal("5.0"), Band.YELLOW),
        (Decimal("7.949"), Decimal("7.9"), Band.YELLOW),
        (Decimal("7.950"), Decimal("8.0"), Band.GREEN),
    ],
)
def test_cs167_banker_round_then_band(
    pre: Decimal,
    rounded_expected: Decimal,
    band_expected: Band,
) -> None:
    rounded = banker_round_score_total(pre)
    assert rounded == rounded_expected
    assert assign_band(rounded) is band_expected


def test_cs167_floating_pipeline_794999_vs_795000() -> None:
    """§2.1 bands after CS-152 1-decimal HALF_EVEN."""
    r_low = banker_round_score_total(Decimal("7.949999"))
    assert r_low == Decimal("7.9")
    assert assign_band(r_low) is Band.YELLOW

    r_high = banker_round_score_total(Decimal("7.950000"))
    assert r_high == Decimal("8.0")
    assert assign_band(r_high) is Band.GREEN


def test_cs167_assign_band_pure_no_override_kw() -> None:
    """Isolation: band mapping is a pure function of the rounded total (CS-157 gated upstream)."""
    import inspect

    sig = inspect.signature(assign_band)
    assert "override" not in str(sig)


# ── CS-168 — B2 APR ladder ──────────────────────────────────────────────


def test_cs168_closed_boundary_convention_doc() -> None:
    """≤9.00% → score 10; (9,10] tier begins immediately above 9."""
    assert b2_annual_rate_score(Decimal("8.99")).score == 10.0
    assert b2_annual_rate_score(Decimal("9.00")).score == 10.0
    assert b2_annual_rate_score(Decimal("9.01")).score == 9.0


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        ("8.99", 10.0),
        ("9.00", 10.0),
        ("9.01", 9.0),
        ("9.99", 9.0),
        ("10.00", 9.0),
        ("10.01", 7.0),
        ("10.99", 7.0),
        ("11.00", 7.0),
        ("11.01", 5.0),
        ("13.99", 5.0),
        ("14.00", 5.0),
        ("14.01", 2.0),
        ("18.99", 2.0),
        ("19.00", 2.0),
        ("19.01", 0.0),
    ],
)
def test_cs168_b2_ladder_table(pct: str, expected: float) -> None:
    assert b2_annual_rate_score(Decimal(pct)).score == pytest.approx(expected)


@pytest.mark.asyncio
async def test_cs168_b2_unverifiable_cites_art19_lit_j() -> None:
    spec = _spec("B2", "B", weight=20.0, worst_unverified=4.0)
    ctx = _ctx(text="Sin cláusulas de interés moratorio.", contract_type="CVP", economic_summary={})
    ev = await category_b.evaluate_b2(spec, ctx)
    assert ev.unverifiable
    assert ev.score == 4.0
    assert "Art. 19 lit. j" in ev.justification


# ── CS-169 — B1 ladder + asymmetric clamp ───────────────────────────────


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        ("10.0", 10.0),
        ("12.0", 8.0),
        ("15.0", 8.0),
        ("15.01", 5.0),
        ("20.0", 5.0),
        ("20.01", 2.0),
        ("35.0", 2.0),
        ("35.01", 0.0),
    ],
)
def test_cs169_b1_ladder_table(pct: str, expected: float) -> None:
    assert b1_down_payment_score(Decimal(pct)).score == pytest.approx(expected)


def test_cs169_asymmetric_pair_8_vs_10_raw_ladder() -> None:
    s8 = b1_down_payment_score(Decimal("8")).score
    s10 = b1_down_payment_score(Decimal("10")).score
    assert s8 >= s10


@pytest.mark.parametrize(
    ("a", "b"),
    [
        (Decimal("9.99"), Decimal("10.00")),
        (Decimal("14.99"), Decimal("15.00")),
        (Decimal("34.99"), Decimal("35.00")),
    ],
)
def test_cs169_boundary_steps_non_increasing(a: Decimal, b: Decimal) -> None:
    assert b1_down_payment_score(a).score >= b1_down_payment_score(b).score


def test_cs169_b1_clamp_raises_favorable_below_benchmark() -> None:
    bench = Decimal("10")
    raw_bad = 5.0  # simulate defective LLM score for a favorable 8 % contract
    out: ClampOutcome = clamp_score(
        criterion_id="B1",
        raw_score=raw_bad,
        inputs=b1_inputs(contract_down_payment_pct=Decimal("8"), benchmark_down_payment_pct=bench),
    )
    assert out.applied
    assert out.score == 10.0


# ── CS-170 — override matrix ───────────────────────────────────────────


async def _positive_ev(
    code: OverrideCode,
    text: str,
    *,
    ctx_extras: dict[str, object] | None = None,
) -> CriterionEvaluation:
    """Dispatch golden-positive fixture to the owning evaluator."""
    mapping: dict[
        OverrideCode,
        tuple[Callable[..., Awaitable[CriterionEvaluation]], CriterionSpec, str, dict[str, object]],
    ] = {
        OverrideCode.ART_1605_CC: (category_a.evaluate_a1, _spec("A1", "A", weight=25.0), "CVC", {}),
        OverrideCode.ART_1613_CC: (category_a.evaluate_a3, _spec("A3", "A", weight=20.0), "CVP", {}),
        OverrideCode.ART_1644_CC: (
            category_c.evaluate_c5,
            _spec("C5", "C", weight=20.0),
            "CVP",
            {"elements_detected": {"warranty_clause": "silent"}},
        ),
        OverrideCode.ART_1425_CC: (
            category_a.evaluate_a6,
            _spec("A6", "A", weight=15.0, applicable_types=("APV", "CVP")),
            "APV",
            {},
        ),
        OverrideCode.ART_3_IVU_FAMILY_HOMESTEAD: (
            category_d.evaluate_d2,
            _spec("D2", "D", weight=15.0),
            "CVP",
            {},
        ),
        OverrideCode.ART_5_LPC_NON_WAIVABLE: (category_e.evaluate_e1, _spec("E1", "E", weight=25.0), "CVP", {}),
        OverrideCode.ART_12_LPC: (category_b.evaluate_b7, _spec("B7", "B", weight=15.0), "CVP", {}),
        OverrideCode.ART_13_LPC: (category_b.evaluate_b9, _spec("B9", "B", weight=10.0), "CVP", {}),
        OverrideCode.ART_18_LPC_BLANK_SIGNATURE: (category_e.evaluate_e6, _spec("E6", "E", weight=15.0), "CVP", {}),
        OverrideCode.ART_17H_LPC_ARBITRATION: (category_e.evaluate_e7, _spec("E7", "E", weight=15.0), "CVP", {}),
        OverrideCode.ART_58_FSV: (category_d.evaluate_d3, _spec("D3", "D", weight=15.0), "CVP", {}),
    }
    fn, spec, ctype, base = mapping[code]
    merged: dict[str, object] = dict(base)
    if ctx_extras:
        for key, val in ctx_extras.items():
            if key == "elements_detected" and isinstance(val, dict):
                inner = dict(merged.get("elements_detected") or {})
                inner.update(val)
                merged["elements_detected"] = inner
            else:
                merged[key] = val
    ctx = _ctx(text=text, contract_type=ctype, **merged)
    return await fn(spec, ctx)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "code",
    list(OverrideCode),
    ids=[c.value for c in OverrideCode],
)
async def test_cs170_positive_triggers_override(code: OverrideCode) -> None:
    name = f"{code.value}_positive.txt"
    text = _load(name)
    ev = await _positive_ev(code, text)
    assert ev.override_triggered is code
    assert ev.score == 0.0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("code", "filename_neg", "extras"),
    [
        (OverrideCode.ART_1605_CC, "art_1605_cc_negative.txt", {}),
        (OverrideCode.ART_1613_CC, "art_1613_cc_negative.txt", {}),
        (OverrideCode.ART_1644_CC, "art_1644_cc_negative.txt", {"elements_detected": {"warranty_clause": "silent"}}),
        (OverrideCode.ART_1425_CC, "art_1425_cc_negative.txt", {}),
        (
            OverrideCode.ART_3_IVU_FAMILY_HOMESTEAD,
            "art_3_ivu_family_homestead_positive.txt",
            {"elements_detected": {"bien_de_familia_cancellation_deed": True}},
        ),
        (OverrideCode.ART_5_LPC_NON_WAIVABLE, "art_5_lpc_non_waivable_negative.txt", {}),
        (OverrideCode.ART_12_LPC, "art_12_lpc_negative.txt", {}),
        (OverrideCode.ART_13_LPC, "art_13_lpc_negative.txt", {}),
        (OverrideCode.ART_18_LPC_BLANK_SIGNATURE, "art_18_lpc_blank_signature_negative.txt", {}),
        (OverrideCode.ART_17H_LPC_ARBITRATION, "art_17h_lpc_arbitration_negative.txt", {}),
        (OverrideCode.ART_58_FSV, "art_58_fsv_negative.txt", {}),
    ],
    ids=[c.value for c in OverrideCode],
)
async def test_cs170_near_miss_excludes_code(
    code: OverrideCode,
    filename_neg: str,
    extras: dict[str, object],
) -> None:
    text = _load(filename_neg)
    ev = await _positive_ev(code, text, ctx_extras=extras)
    assert ev.override_triggered is not code


@pytest.mark.parametrize("code", list(OverrideCode))
def test_cs170_positive_with_perfect_peer_collapses_total(code: OverrideCode) -> None:
    text = _load(f"{code.value}_positive.txt")
    trigger = _run(_positive_ev(code, text))
    peer = CriterionEvaluation(
        criterion_id="Z9",
        category="F",
        applicable=True,
        evaluated=True,
        unverifiable=False,
        score=10.0,
        weight_in_category=10.0,
        override_triggered=None,
        justification="Synthetic perfect peer for aggregation isolation.",
    )
    combo = aggregate_total([trigger, peer])
    assert combo.score_total == 0.0
    assert combo.band is Band.RED
    assert code in combo.override_triggered


# ── CS-171 — Hypothesis monotonicity (buyer-favorable direction) ───────


def _clamp_b1(pct: Decimal, raw: float) -> float:
    return clamp_score(
        criterion_id="B1",
        raw_score=raw,
        inputs=b1_inputs(
            contract_down_payment_pct=pct,
            benchmark_down_payment_pct=Decimal("10"),
        ),
    ).score


def _clamp_b2(rate: Decimal, raw: float) -> float:
    return clamp_score(
        criterion_id="B2",
        raw_score=raw,
        inputs=b2_inputs(contract_annual_rate_pct=rate, benchmark_segment_mid_pct=Decimal("9")),
    ).score


def _clamp_b4(mult: Decimal, raw: float) -> float:
    return clamp_score(
        criterion_id="B4",
        raw_score=raw,
        inputs=b4_inputs(
            contract_total_cost_multiplier=mult,
            benchmark_healthy_max_multiplier=Decimal("1.5"),
        ),
    ).score


def _clamp_b3(months: Decimal, raw: float) -> float:
    return clamp_score(
        criterion_id="B3",
        raw_score=raw,
        inputs=b3_inputs(
            contract_term_months=months,
            benchmark_reasonable_max_months=Decimal("240"),  # 20y — top of “reasonable” band
        ),
    ).score


dec_pct = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("60.00"), places=2, allow_nan=False)
dec_rate = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("30.00"), places=2, allow_nan=False)
dec_mult = st.decimals(min_value=Decimal("1.0"), max_value=Decimal("4.0"), places=2, allow_nan=False)
dec_months = st.decimals(min_value=Decimal("60"), max_value=Decimal("360"), places=0, allow_nan=False)


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(p1=dec_pct, p2=dec_pct)
def test_cs171_b1_monotone_after_clamp(p1: Decimal, p2: Decimal) -> None:
    assume(p1 < p2)
    s1 = _clamp_b1(p1, b1_down_payment_score(p1).score)
    s2 = _clamp_b1(p2, b1_down_payment_score(p2).score)
    assert s1 + 1e-9 >= s2, f"B1 monotonicity fail pct1={p1} pct2={p2} s1={s1} s2={s2}"


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(r1=dec_rate, r2=dec_rate)
def test_cs171_b2_monotone_after_clamp(r1: Decimal, r2: Decimal) -> None:
    assume(r1 < r2)
    s1 = _clamp_b2(r1, b2_annual_rate_score(r1).score)
    s2 = _clamp_b2(r2, b2_annual_rate_score(r2).score)
    assert s1 + 1e-9 >= s2, f"B2 monotonicity fail r1={r1} r2={r2} s1={s1} s2={s2}"


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(m1=dec_mult, m2=dec_mult)
def test_cs171_b4_monotone_after_clamp(m1: Decimal, m2: Decimal) -> None:
    assume(m1 < m2)
    s1 = _clamp_b4(m1, b4_total_cost_score(m1).score)
    s2 = _clamp_b4(m2, b4_total_cost_score(m2).score)
    assert s1 + 1e-9 >= s2, f"B4 monotonicity fail m1={m1} m2={m2} s1={s1} s2={s2}"


@settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
@given(a=dec_months, b=dec_months)
def test_cs171_b3_monotone_after_clamp_within_ivu_leg(a: Decimal, b: Decimal) -> None:
    assume(a <= b)
    ya = a / Decimal("12")
    yb = b / Decimal("12")
    assume(ya >= Decimal("5") and yb <= Decimal("30"))
    s1 = _clamp_b3(a, b3_term_score(ya).score)
    s2 = _clamp_b3(b, b3_term_score(yb).score)
    assert s1 + 1e-9 >= s2, f"B3 monotonicity fail months1={a} months2={b} s1={s1} s2={s2}"


@pytest.mark.slow
@settings(max_examples=2000, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(p1=dec_pct, p2=dec_pct)
def test_cs171_b1_monotone_nightly_volume(p1: Decimal, p2: Decimal) -> None:
    assume(p1 < p2)
    s1 = _clamp_b1(p1, b1_down_payment_score(p1).score)
    s2 = _clamp_b1(p2, b1_down_payment_score(p2).score)
    assert s1 + 1e-9 >= s2
