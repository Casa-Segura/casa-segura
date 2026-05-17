"""CS-137: renormalizer + insufficient_data path coverage.

Test intent (Rule 9): `test_unknown_slots_never_substitute_zero` is the
binding honesty guard for PRD_F5 BR-09 — if any future refactor allows the
assembler to fill `price_cash = 0` or `monthly_payment = 0` for unknown
inputs, the test fails. PRD_F5 §1 third bullet binds this contract.

BVA: `test_down_payment_cross_check_boundary` pins the inclusive-at-5%
tolerance for the BR-07-style cross-check between `down_payment_usd` and
`purchase_price_usd * down_payment_pct`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.contract_type import ContractType
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.application.analyzer import analyze
from economics.application.benchmark_loader import load_yaml, upsert_benchmarks
from economics.application.catalog import BenchmarkCatalog
from economics.application.renormalizer import (
    WARNING_DOWN_PAYMENT_INCONSISTENT,
    WARNING_TOTAL_COST_NOT_DISCLOSED,
    detect_precursors,
)
from economics.application.total_cost import compute_total_cost
from economics.domain.economic_summary import DerivationStatus


REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_FIXTURE = REPO_ROOT / "backend" / "fixtures" / "economic_benchmarks_2026q2.yaml"


def _slot(name: str, value, status=ExtractionStatus.PRESENT) -> EconomicSlot:
    return EconomicSlot(field_name=name, status=status, value=value, confidence=0.9)


def _extraction(**slot_values) -> AggregatedExtraction:
    slots = {name: _slot(name, val) for name, val in slot_values.items() if val is not None}
    return AggregatedExtraction(contract_type=ContractType.CVP, slots=slots)


@pytest.fixture
def catalog(db) -> BenchmarkCatalog:
    payload = load_yaml(PRODUCTION_FIXTURE)
    version_obj, *_ = upsert_benchmarks(payload, activate=True)
    return BenchmarkCatalog.from_db(version_obj)


# ─── Down payment cross-check ────────────────────────────────────────────────


def test_down_payment_consistent_yields_no_warning():
    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=8_000,
        down_payment_pct=0.10,
    )
    bundle = compute_total_cost(extraction, annual_rate_pct=None)

    precursors = detect_precursors(extraction, bundle)

    assert WARNING_DOWN_PAYMENT_INCONSISTENT not in precursors


@pytest.mark.parametrize(
    ("down_payment", "expected_warning"),
    [
        # |8000 - 80000*0.10| / 80000 = 0 → consistent.
        (8_000, False),
        # |12000 - 8000| / 80000 = 0.05 → exactly 5% → inclusive-coherent.
        (12_000, False),
        # |12001 - 8000| / 80000 = 0.0500125 → breach (>5%).
        (12_001, True),
    ],
)
def test_down_payment_cross_check_boundary(down_payment: float, expected_warning: bool):
    extraction = _extraction(
        purchase_price_usd=80_000,
        down_payment_usd=down_payment,
        down_payment_pct=0.10,
    )
    bundle = compute_total_cost(extraction, annual_rate_pct=None)

    precursors = detect_precursors(extraction, bundle)

    if expected_warning:
        assert WARNING_DOWN_PAYMENT_INCONSISTENT in precursors
    else:
        assert WARNING_DOWN_PAYMENT_INCONSISTENT not in precursors


def test_down_payment_check_skipped_without_pct():
    extraction = _extraction(purchase_price_usd=80_000, down_payment_usd=99_999)
    bundle = compute_total_cost(extraction, annual_rate_pct=None)

    precursors = detect_precursors(extraction, bundle)

    assert WARNING_DOWN_PAYMENT_INCONSISTENT not in precursors


# ─── Total cost not disclosed ────────────────────────────────────────────────


def test_total_cost_not_disclosed_fires_when_term_present_but_no_total():
    """Term mentioned but `total_cost_paid` cannot be computed → flag the gap."""

    extraction = _extraction(purchase_price_usd=80_000, term_months=240)
    bundle = compute_total_cost(extraction, annual_rate_pct=None)

    precursors = detect_precursors(extraction, bundle)

    assert WARNING_TOTAL_COST_NOT_DISCLOSED in precursors


def test_total_cost_not_disclosed_silent_when_no_financing_signal():
    """Cash-only contract is not "missing a total" — it has no financing at all."""

    extraction = _extraction(purchase_price_usd=80_000)
    bundle = compute_total_cost(extraction, annual_rate_pct=None)

    precursors = detect_precursors(extraction, bundle)

    assert WARNING_TOTAL_COST_NOT_DISCLOSED not in precursors


# ─── End-to-end: assembler folds the precursors into final warnings ──────────


@pytest.mark.django_db
def test_assembler_emits_down_payment_inconsistent_warning(catalog):
    """End-to-end through `analyze()`: precursors land as structured warnings."""

    extraction = AggregatedExtraction(
        contract_type=ContractType.CVP,
        slots={
            "purchase_price_usd": _slot("purchase_price_usd", 80_000),
            "down_payment_usd": _slot("down_payment_usd", 20_000),  # 25% in dollars
            "down_payment_pct": _slot("down_payment_pct", 0.10),  # 10% — mismatch
            "term_months": _slot("term_months", 240),
            "interest_rate_pct": _slot("interest_rate_pct", 0.09),
            "monthly_payment_usd": _slot("monthly_payment_usd", 540.0),
        },
    )

    summary = analyze(extraction, catalog=catalog)

    warning_codes = {w.code for w in summary.warnings}
    assert "down_payment_inconsistent" in warning_codes


# ─── BR-09 honesty guard (Rule 9 anchor) ─────────────────────────────────────


@pytest.mark.django_db
def test_unknown_slots_never_substitute_zero(catalog):
    """Rule 9 — BR-09 binding test.

    With no slots present, the summary must report `insufficient_data` and
    leave `fields_extracted` / `fields_derived` with all-`None` slots — NEVER
    substitute zeros for unknown price / payment.
    """

    extraction = AggregatedExtraction(contract_type=ContractType.CVP, slots={})

    summary = analyze(extraction, catalog=catalog)

    assert summary.derivation_status == DerivationStatus.INSUFFICIENT_DATA
    # PRD_F5 §1: every persisted numeric must be `null`, never a fabricated zero.
    assert summary.fields_extracted.price_cash is None
    assert summary.fields_extracted.monthly_payment is None
    assert summary.fields_extracted.financed_amount is None
    assert summary.fields_derived.total_cost_paid is None
    assert summary.fields_derived.monthly_payment_theoretical is None
    assert summary.benchmark_comparisons == ()
    assert summary.overcost is None


@pytest.mark.django_db
def test_insufficient_data_envelope_matches_contract_fixture(catalog):
    """The shape we emit on the empty path equals the cross-team fixture."""

    extraction = AggregatedExtraction(contract_type=ContractType.CVP, slots={})

    summary = analyze(extraction, catalog=catalog)
    payload = summary.model_dump(mode="json")

    # Per `docs/fixtures/economic-summary/summary-insufficient-data.json`:
    assert payload["derivation_status"] == "insufficient_data"
    # `model_dump(mode="json")` keeps explicit-None as None; the persisted
    # JSON encoder will turn `null` into `null` and an empty `BaseModel`
    # into a `{}`-equivalent.
    assert payload["benchmark_comparisons"] == []
    assert payload["warnings"] != []  # at least `annual_rate_not_expressed`
    assert payload["overcost"] is None
    assert payload["benchmark_version"] == "2026-Q2"


def test_renormalizer_imports_no_llm_gateway():
    """BR-13 guard — `economics.application.renormalizer` must not pull in OpenRouter.

    A regression in this guard means an engineer introduced an LLM call into
    the deterministic F5 path. PRD_F5 BR-13 forbids it.
    """

    import economics.application.renormalizer as renormalizer_module

    module_source = Path(renormalizer_module.__file__).read_text(encoding="utf-8")
    assert "openrouter" not in module_source.lower()
    assert "OpenRouterClient" not in module_source
