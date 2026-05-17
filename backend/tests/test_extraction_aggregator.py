"""CS-116 — pure-domain tests for `aggregate_extraction`.

Covers AC1 (status precedence: AMBIGUOUS > INVALID > NOT_PRESENT > PRESENT),
AC2 (ambiguous_count metric), AC3 (`interest_calculation_base_unfavorable`
precursor), and the BVA boundary at the F5 not-present cutoff.

Rule 9 invariants:
    - `test_no_silent_zero_default`            — never substitute 0 for missing
    - `test_economics_cutoff_inclusive_at_0_50` — 0.50 is PRESENT, 0.49 is NOT_PRESENT
    - `test_precursor_requires_total_balance`  — the AC3 warning needs both signals
"""

from __future__ import annotations

import pytest

from classification.application.extraction_aggregator import (
    WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE,
    aggregate_extraction,
)
from classification.domain.confidence import ConfidenceBand
from classification.domain.contract_extraction import ContractExtraction
from classification.domain.contract_type import ContractType
from classification.domain.extracted_fields import ExtractedFields
from classification.domain.extraction_status import ExtractionStatus


def _band(score: float, rationale: str | None = None) -> ConfidenceBand:
    return ConfidenceBand.from_score(score, rationale=rationale)


# ---------------------------------------------------------------------------
# Empty extraction — all relevant slots default to NOT_PRESENT
# ---------------------------------------------------------------------------


def test_empty_extraction_all_slots_not_present():
    extraction = ContractExtraction(contract_type=ContractType.CVP)

    aggregated = aggregate_extraction(extraction)

    assert all(slot.status is ExtractionStatus.NOT_PRESENT for slot in aggregated.slots.values())
    assert aggregated.ambiguous_count == 0
    assert aggregated.warning_precursors == []
    # All required CVP fields appear as slots.
    assert "purchase_price_usd" in aggregated.slots


# ---------------------------------------------------------------------------
# Rule 9 — no silent zero substitution
# ---------------------------------------------------------------------------


def test_no_silent_zero_default():
    """A missing money field must surface as NOT_PRESENT, NOT zero.

    Substituting `0.0` for `None` is the bug PRD_F5 BR-09 was written to
    prevent. This test snapshots that contract: the aggregator preserves
    `value=None` and signals it via status, never via a numeric zero.
    """
    extraction = ContractExtraction(contract_type=ContractType.CVP)
    aggregated = aggregate_extraction(extraction)

    for slot in aggregated.slots.values():
        # Money / int slots should keep their `None` — never coerced to 0.
        assert slot.value is None
        assert slot.status is not ExtractionStatus.PRESENT


# ---------------------------------------------------------------------------
# BVA — economics cutoff at 0.50
# ---------------------------------------------------------------------------


def test_economics_cutoff_inclusive_at_0_50():
    """Score exactly at the F5 cutoff (0.50) keeps the field PRESENT.

    Both the value and the band are needed; CS-114 publishes the constant
    `ECONOMICS_NOT_PRESENT_CUTOFF = 0.5`, and the aggregator uses
    `confidence < 0.5` (strict <) so the cutoff itself stays on the
    PRESENT side. 0.499 falls through to NOT_PRESENT.
    """
    above = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(monthly_payment_usd=1000.0),
        field_confidences={"monthly_payment_usd": _band(0.50)},
    )
    below = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(monthly_payment_usd=1000.0),
        field_confidences={"monthly_payment_usd": _band(0.499)},
    )

    assert aggregate_extraction(above).slots["monthly_payment_usd"].status is ExtractionStatus.PRESENT
    assert aggregate_extraction(below).slots["monthly_payment_usd"].status is ExtractionStatus.NOT_PRESENT


# ---------------------------------------------------------------------------
# Status precedence — AMBIGUOUS > INVALID > NOT_PRESENT > PRESENT
# ---------------------------------------------------------------------------


def test_ambiguous_takes_precedence_over_invalid_and_not_present():
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(),  # all None
        field_confidences={},
        unverifiable_fields=["monthly_payment_usd"],  # would be INVALID
        ambiguous_fields=["monthly_payment_usd"],  # overrides
    )
    aggregated = aggregate_extraction(extraction)

    assert aggregated.slots["monthly_payment_usd"].status is ExtractionStatus.AMBIGUOUS
    assert aggregated.ambiguous_count == 1


def test_invalid_when_value_none_and_in_unverifiable():
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(),
        field_confidences={},
        unverifiable_fields=["purchase_price_usd"],
    )
    aggregated = aggregate_extraction(extraction)

    assert aggregated.slots["purchase_price_usd"].status is ExtractionStatus.INVALID


def test_present_when_value_and_confidence_above_cutoff():
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(purchase_price_usd=80000.0),
        field_confidences={"purchase_price_usd": _band(0.92)},
    )
    aggregated = aggregate_extraction(extraction)

    slot = aggregated.slots["purchase_price_usd"]
    assert slot.status is ExtractionStatus.PRESENT
    assert slot.value == pytest.approx(80000.0)
    assert slot.confidence == pytest.approx(0.92)


def test_value_present_but_confidence_missing_routes_to_not_present():
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(monthly_payment_usd=1200.0),
        field_confidences={},  # no band
    )
    aggregated = aggregate_extraction(extraction)

    assert aggregated.slots["monthly_payment_usd"].status is ExtractionStatus.NOT_PRESENT


# ---------------------------------------------------------------------------
# AC3 — `interest_calculation_base_unfavorable` precursor
# ---------------------------------------------------------------------------


def test_precursor_fires_when_total_balance_and_rate_missing():
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(interest_calculation_base="total_balance"),
        field_confidences={"interest_calculation_base": _band(0.9)},
    )
    aggregated = aggregate_extraction(extraction)

    assert WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE in aggregated.warning_precursors


def test_precursor_does_not_fire_when_rate_is_present():
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(
            interest_calculation_base="total_balance",
            monthly_rate_pct=0.012,
        ),
        field_confidences={
            "interest_calculation_base": _band(0.9),
            "monthly_rate_pct": _band(0.85),
        },
    )
    aggregated = aggregate_extraction(extraction)

    assert WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE not in aggregated.warning_precursors


def test_precursor_requires_total_balance():
    """Rule 9: the precursor fires only on `total_balance`, never on `outstanding_principal`."""
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(interest_calculation_base="outstanding_principal"),
        field_confidences={"interest_calculation_base": _band(0.9)},
    )
    aggregated = aggregate_extraction(extraction)

    assert WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE not in aggregated.warning_precursors


def test_precursor_requires_base_present_not_ambiguous():
    """If the calculation base itself is ambiguous, the precursor must not fire.

    Otherwise we would warn EPIC-05 about an Art. 12 LPC risk on a
    contract whose calculation base is itself uncertain. The aggregator
    must wait until the base is unambiguously `total_balance`.
    """
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(),
        ambiguous_fields=["interest_calculation_base"],
    )
    aggregated = aggregate_extraction(extraction)

    assert WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE not in aggregated.warning_precursors


# ---------------------------------------------------------------------------
# `unverifiable_fields` projection
# ---------------------------------------------------------------------------


def test_unverifiable_fields_projection_excludes_present_slots_only():
    extraction = ContractExtraction(
        contract_type=ContractType.CVP,
        extracted_fields=ExtractedFields(purchase_price_usd=80000.0),
        field_confidences={"purchase_price_usd": _band(0.95)},
    )
    aggregated = aggregate_extraction(extraction)

    assert "purchase_price_usd" not in aggregated.unverifiable_fields
    # Every non-PRESENT slot lands here, including all the required-but-missing ones.
    for name, slot in aggregated.slots.items():
        if slot.status is ExtractionStatus.PRESENT:
            assert name not in aggregated.unverifiable_fields
        else:
            assert name in aggregated.unverifiable_fields
