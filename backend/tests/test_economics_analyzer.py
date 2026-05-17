"""CS-135: EconomicSummary assembler coverage + JSON contract parity.

Test intent (Rule 9): `test_summary_keys_match_contract_schema` asserts the
exact top-level key set persisted in `economic_summary` matches the
authoritative `ECONOMIC_SUMMARY_CONTRACT.md` table. If a developer renames
`fields_derived` → `derived_fields` (or similar drift), the test fails and
the FE/BE contract is preserved.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.contract_type import ContractType
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.application.analyzer import analyze
from economics.application.benchmark_loader import load_yaml, upsert_benchmarks
from economics.application.catalog import BenchmarkCatalog
from economics.domain.economic_summary import DerivationStatus, EconomicSummary

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_FIXTURE = REPO_ROOT / "backend" / "fixtures" / "economic_benchmarks_2026q2.yaml"


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _slot(name: str, value, status=ExtractionStatus.PRESENT, confidence=0.9) -> EconomicSlot:
    return EconomicSlot(field_name=name, status=status, value=value, confidence=confidence)


def _full_extraction() -> AggregatedExtraction:
    return AggregatedExtraction(
        contract_type=ContractType.CVP,
        slots={
            "purchase_price_usd": _slot("purchase_price_usd", 80_000),
            "down_payment_usd": _slot("down_payment_usd", 8_000),
            "down_payment_pct": _slot("down_payment_pct", 0.1),
            "financed_amount_usd": _slot("financed_amount_usd", 72_000),
            "term_months": _slot("term_months", 240),
            "interest_rate_pct": _slot("interest_rate_pct", 0.18),
            "monthly_payment_usd": _slot("monthly_payment_usd", 1083.50),
            "payment_periodicity": _slot("payment_periodicity", "monthly"),
            "interest_calculation_base": _slot("interest_calculation_base", "total_balance"),
        },
        warning_precursors=["interest_calculation_base_unfavorable"],
    )


@pytest.fixture
def catalog(db) -> BenchmarkCatalog:
    payload = load_yaml(PRODUCTION_FIXTURE)
    version_obj, *_ = upsert_benchmarks(payload, activate=True)
    return BenchmarkCatalog.from_db(version_obj)


# ─── Top-level contract parity (Rule 9 anchor) ───────────────────────────────


# The cross-team contract from ECONOMIC_SUMMARY_CONTRACT.md — these are the
# only keys the persisted JSON should carry.
CONTRACT_KEYS = {
    "contract_type",
    "currency",
    "currency_conversion_note",
    "derivation_status",
    "fields_extracted",
    "fields_derived",
    "benchmark_comparisons",
    "overcost",
    "warnings",
    "benchmark_version",
}


def test_summary_keys_match_contract_schema():
    """Field rename / drift guard for `ECONOMIC_SUMMARY_CONTRACT.md`."""

    assert set(EconomicSummary.model_fields.keys()) == CONTRACT_KEYS


def test_summary_forbids_unknown_keys():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EconomicSummary.model_validate(
            {
                "contract_type": "CVP",
                "currency": "USD",
                "benchmark_version": "2026-Q2",
                "extra_unknown_key": "boom",
            }
        )


# ─── Happy path ──────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_full_extraction_produces_full_summary(catalog):
    summary = analyze(_full_extraction(), catalog=catalog)

    assert summary.contract_type == ContractType.CVP
    assert summary.benchmark_version == "2026-Q2"
    assert summary.derivation_status == DerivationStatus.FULL
    assert summary.fields_extracted.price_cash == Decimal("80000.0000")
    assert summary.fields_derived.total_cost_vs_cash_multiplier is not None
    # 18% contract vs 8% bank mid → 10pp delta → well_above_market.
    assert any(
        c.metric == "annual_rate" and c.assessment == "well_above_market" for c in summary.benchmark_comparisons
    )
    # Overcost present and positive (BR-02 — not skipped because contract > benchmark).
    assert summary.overcost is not None
    assert summary.overcost.vs_benchmark_usd > Decimal("0")


@pytest.mark.django_db
def test_summary_roundtrips_through_json(catalog):
    summary = analyze(_full_extraction(), catalog=catalog)

    encoded = summary.model_dump_json()
    decoded = EconomicSummary.model_validate(json.loads(encoded))

    assert decoded == summary


@pytest.mark.django_db
def test_warning_dedup_by_code_and_related_field(catalog):
    extraction = AggregatedExtraction(
        contract_type=ContractType.CVP,
        slots={},  # no rate slots → annual_rate_not_expressed fires
        warning_precursors=[
            "annual_rate_not_expressed",
            "annual_rate_not_expressed",  # duplicate — must be deduped
        ],
    )

    summary = analyze(extraction, catalog=catalog)

    code_count = sum(1 for w in summary.warnings if w.code == "annual_rate_not_expressed")
    assert code_count == 1


@pytest.mark.django_db
def test_no_slots_yields_insufficient_data(catalog):
    extraction = AggregatedExtraction(contract_type=ContractType.CVP, slots={})

    summary = analyze(extraction, catalog=catalog)

    assert summary.derivation_status == DerivationStatus.INSUFFICIENT_DATA
    assert summary.benchmark_comparisons == ()
    assert summary.overcost is None
    # `annual_rate_not_expressed` precursor is emitted by rate_normalizer.
    assert any(w.code == "annual_rate_not_expressed" for w in summary.warnings)


@pytest.mark.django_db
def test_below_market_skips_overcost(catalog):
    extraction = AggregatedExtraction(
        contract_type=ContractType.CVP,
        slots={
            "purchase_price_usd": _slot("purchase_price_usd", 80_000),
            "down_payment_usd": _slot("down_payment_usd", 8_000),
            "financed_amount_usd": _slot("financed_amount_usd", 72_000),
            "term_months": _slot("term_months", 240),
            "interest_rate_pct": _slot("interest_rate_pct", 0.05),  # below bank mid 8%
            "monthly_payment_usd": _slot("monthly_payment_usd", 475.0),
        },
    )

    summary = analyze(extraction, catalog=catalog)

    assert summary.overcost is None  # BR-02 asymmetric
    # The comparison row still exists and reports favorable status.
    rate_row = next(c for c in summary.benchmark_comparisons if c.metric == "annual_rate")
    assert rate_row.assessment == "below_market_favorable"


@pytest.mark.django_db
def test_benchmark_version_echoes_byte_equal(catalog):
    """CS-136 precursor — assembler must echo the catalog version string verbatim."""

    summary = analyze(_full_extraction(), catalog=catalog)

    assert summary.benchmark_version == catalog.version == "2026-Q2"


@pytest.mark.django_db
def test_currency_default_when_slot_absent(catalog):
    """Contract is silent → default to USD per ECONOMIC_SUMMARY_CONTRACT.md."""

    extraction = AggregatedExtraction(contract_type=ContractType.CVP, slots={})

    summary = analyze(extraction, catalog=catalog)

    assert summary.currency == "USD"
