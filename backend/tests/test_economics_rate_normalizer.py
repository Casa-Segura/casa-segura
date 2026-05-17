"""CS-131: deterministic annual-rate normalization coverage.

Test intent (Rule 9): the golden vector `monthly = 0.015 → annual = 0.19562`
proves compound vs linear drift — if a developer swaps `(1+m)^12 - 1` for
`12 * m` the answer drops to `0.18` and `test_compound_vs_linear_guard` fails
loudly. PRD_F5 BR-05 is the binding citation.

BVA boundaries from PRD_F5 US-01: `[0, 1]` inclusive, anything outside is
INVALID. The `m → annual` overflow case is exercised separately.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.contract_type import ContractType
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.application.rate_normalizer import (
    WARNING_ANNUAL_INCONSISTENT_WITH_MONTHLY,
    WARNING_ANNUAL_NOT_EXPRESSED,
    normalize_annual_rate,
)

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _slot(name: str, value: float | None, status: ExtractionStatus, confidence: float = 0.9) -> EconomicSlot:
    return EconomicSlot(
        field_name=name,
        status=status,
        value=value,
        confidence=confidence,
        rationale=None,
    )


def _extraction(**slots: EconomicSlot) -> AggregatedExtraction:
    return AggregatedExtraction(
        contract_type=ContractType.CVP,
        slots=dict(slots),
    )


# ─── Happy paths ─────────────────────────────────────────────────────────────


def test_annual_only_passes_through():
    extraction = _extraction(
        interest_rate_pct=_slot("interest_rate_pct", 0.09, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.PRESENT
    assert result.annual_rate_pct == Decimal("0.0900")
    assert result.derivation_note == "extracted_annual"
    assert result.warning_precursors == ()


def test_monthly_only_compound_conversion():
    """Golden vector: `(1.015)^12 - 1 = 0.195618...` → quantized to 0.1956."""

    extraction = _extraction(
        monthly_rate_pct=_slot("monthly_rate_pct", 0.015, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.PRESENT
    assert result.annual_rate_pct == Decimal("0.1956")
    assert result.derivation_note == "converted_from_monthly_compound"


def test_compound_vs_linear_guard():
    """Rule 9 — fails if formula gets swapped to linear `12 * monthly`.

    Linear would yield 0.18 (quantized to Decimal("0.1800")); compound yields
    0.1956. PRD_F5 BR-05 binds the compound formula.
    """

    extraction = _extraction(
        monthly_rate_pct=_slot("monthly_rate_pct", 0.015, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.annual_rate_pct != Decimal("0.1800"), (
        "regression — compound formula collapsed to linear `12*m`; PRD_F5 BR-05"
    )


def test_annual_takes_precedence_when_both_consistent():
    """When both slots are PRESENT and agree within tolerance, prefer annual."""

    extraction = _extraction(
        interest_rate_pct=_slot("interest_rate_pct", 0.19562, ExtractionStatus.PRESENT),
        monthly_rate_pct=_slot("monthly_rate_pct", 0.015, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.PRESENT
    assert result.derivation_note == "extracted_annual"
    assert result.warning_precursors == ()


def test_annual_inconsistent_with_monthly_emits_warning():
    """Annual = 0.05 but monthly = 0.015 (would compound to 0.1956). Mismatch."""

    extraction = _extraction(
        interest_rate_pct=_slot("interest_rate_pct", 0.05, ExtractionStatus.PRESENT),
        monthly_rate_pct=_slot("monthly_rate_pct", 0.015, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.PRESENT
    assert result.annual_rate_pct == Decimal("0.0500")
    assert WARNING_ANNUAL_INCONSISTENT_WITH_MONTHLY in result.warning_precursors


# ─── BVA: PRD_F5 US-01 range boundaries ──────────────────────────────────────


@pytest.mark.parametrize("annual_value", [0.0, 1.0])
def test_annual_inclusive_boundaries_pass(annual_value: float):
    extraction = _extraction(
        interest_rate_pct=_slot("interest_rate_pct", annual_value, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.PRESENT


@pytest.mark.parametrize("annual_value", [-0.001, 1.01])
def test_annual_out_of_range_is_invalid(annual_value: float):
    extraction = _extraction(
        interest_rate_pct=_slot("interest_rate_pct", annual_value, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.INVALID
    assert result.annual_rate_pct is None
    assert result.derivation_note == "invalid_annual_out_of_range"


def test_monthly_zero_yields_annual_zero():
    extraction = _extraction(
        monthly_rate_pct=_slot("monthly_rate_pct", 0.0, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.PRESENT
    assert result.annual_rate_pct == Decimal("0.0000")


def test_monthly_overflow_marks_invalid():
    """`(1.1)^12 - 1 ≈ 2.138` — outside the [0,1] annual window."""

    extraction = _extraction(
        monthly_rate_pct=_slot("monthly_rate_pct", 0.1, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.INVALID
    assert result.derivation_note == "invalid_compound_overflow"


def test_negative_monthly_marks_invalid():
    extraction = _extraction(
        monthly_rate_pct=_slot("monthly_rate_pct", -0.001, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.INVALID
    assert result.derivation_note == "invalid_monthly_out_of_range"


# ─── NOT_PRESENT / non-PRESENT slot handling ─────────────────────────────────


def test_no_slots_marks_not_expressed():
    extraction = _extraction()

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.NOT_PRESENT
    assert result.annual_rate_pct is None
    assert WARNING_ANNUAL_NOT_EXPRESSED in result.warning_precursors


def test_ambiguous_slot_treated_as_not_present():
    """PRD_F5 US-01: non-PRESENT slots are not consumed even if `.value` carries a number."""

    extraction = _extraction(
        interest_rate_pct=_slot("interest_rate_pct", 0.09, ExtractionStatus.AMBIGUOUS, confidence=0.4),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.NOT_PRESENT
    assert WARNING_ANNUAL_NOT_EXPRESSED in result.warning_precursors


def test_invalid_annual_does_not_fall_back_to_monthly_silently():
    """When the explicit annual is present-but-invalid, do not silently swap to monthly.

    Surfacing the INVALID lets the assembler emit a structured warning. The
    monthly value can still be carried as a diagnostic slot by CS-135.
    """

    extraction = _extraction(
        interest_rate_pct=_slot("interest_rate_pct", 1.5, ExtractionStatus.PRESENT),
        monthly_rate_pct=_slot("monthly_rate_pct", 0.015, ExtractionStatus.PRESENT),
    )

    result = normalize_annual_rate(extraction)

    assert result.status == ExtractionStatus.INVALID
    assert result.derivation_note == "invalid_annual_out_of_range"


# ─── Determinism ─────────────────────────────────────────────────────────────


def test_determinism_byte_equal_serialization():
    """Same inputs produce byte-equal JSON across invocations."""

    extraction = _extraction(
        monthly_rate_pct=_slot("monthly_rate_pct", 0.015, ExtractionStatus.PRESENT),
    )

    a = normalize_annual_rate(extraction).model_dump_json()
    b = normalize_annual_rate(extraction).model_dump_json()

    assert a == b
