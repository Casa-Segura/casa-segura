"""CS-114 — pydantic schemas for the classification envelope.

Covers AC1 (enum closure on `contract_type`), AC2 (`confidence` reject
out-of-range), AC3 (`is_not_present_for_economics` 0.5 BVA), and AC4
(`ElementsDetected` closed catalogue + `IndicatorsFound` shape).

Rule 9 invariants tested:
    - `test_contract_type_enum_closed`           — adding `SUBLEASE` requires rubric coordination
    - `test_confidence_band_lower_inclusive`     — 0.65 is MEDIUM, not LOW
    - `test_confidence_band_upper_strict`        — 0.85 is HIGH, not MEDIUM
    - `test_economics_not_present_cutoff_bva`    — 0.499 not_present, 0.500 present
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from classification.domain.confidence import (
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
    ECONOMICS_NOT_PRESENT_CUTOFF,
    ConfidenceBand,
    ConfidenceLevel,
)
from classification.domain.contract_extraction import ContractExtraction
from classification.domain.contract_type import ContractType
from classification.domain.dtos import ClassificationResult
from classification.domain.elements_detected import ElementsDetected
from classification.domain.indicators import (
    MAX_INDICATOR_LENGTH,
    MAX_INDICATORS,
    IndicatorsFound,
)

# ---------------------------------------------------------------------------
# ContractType — enum closure (CS-114 AC1, Rule 9)
# ---------------------------------------------------------------------------


def test_contract_type_enum_closed():
    """RUBRICA §3 enum closure: `SUBLEASE` (or any other) must fail validation."""
    with pytest.raises(ValidationError):
        ClassificationResult.model_validate(
            {"contract_type": "SUBLEASE", "confidence": 0.9},
        )


def test_contract_type_accepts_all_nine_outcomes():
    for value in (
        ContractType.CVC,
        ContractType.CVP,
        ContractType.ARV,
        ContractType.ARC,
        ContractType.APV,
        ContractType.LEA,
        ContractType.IVU,
        ContractType.FSV,
        ContractType.NOT_CLASSIFIABLE,
    ):
        result = ClassificationResult(contract_type=value, confidence=0.9)
        assert result.contract_type is value


# ---------------------------------------------------------------------------
# ConfidenceBand — out-of-range reject + threshold constants (CS-114 AC2)
# ---------------------------------------------------------------------------


def test_confidence_band_rejects_out_of_range():
    with pytest.raises(ValidationError):
        ConfidenceBand(level=ConfidenceLevel.HIGH, score=1.01)
    with pytest.raises(ValidationError):
        ConfidenceBand(level=ConfidenceLevel.HIGH, score=-0.01)


def test_confidence_band_upper_strict():
    """Score exactly at the HIGH threshold is HIGH (inclusive lower bound of HIGH)."""
    assert CONFIDENCE_HIGH_THRESHOLD == pytest.approx(0.85)
    assert ConfidenceBand.level_from_score(0.85) is ConfidenceLevel.HIGH
    assert ConfidenceBand.level_from_score(0.8499) is ConfidenceLevel.MEDIUM


def test_confidence_band_lower_inclusive():
    """0.65 is MEDIUM (inclusive lower bound); 0.6499 is LOW."""
    assert CONFIDENCE_MEDIUM_THRESHOLD == pytest.approx(0.65)
    assert ConfidenceBand.level_from_score(0.65) is ConfidenceLevel.MEDIUM
    assert ConfidenceBand.level_from_score(0.6499) is ConfidenceLevel.LOW


# ---------------------------------------------------------------------------
# is_not_present_for_economics — 0.499 vs 0.500 BVA (CS-114 AC3, CS-116 AC)
# ---------------------------------------------------------------------------


def test_economics_not_present_cutoff_bva():
    assert ECONOMICS_NOT_PRESENT_CUTOFF == pytest.approx(0.5)
    assert ConfidenceBand.from_score(0.499).is_not_present_for_economics() is True
    assert ConfidenceBand.from_score(0.500).is_not_present_for_economics() is False
    assert ConfidenceBand.from_score(0.501).is_not_present_for_economics() is False


# ---------------------------------------------------------------------------
# ElementsDetected — closed catalogue (CS-114 AC4)
# ---------------------------------------------------------------------------


EXPECTED_ELEMENT_KEYS = frozenset(
    {
        "public_deed",
        "arbitration_clause",
        "warranty_exemption_clause",
        "blank_signature_clause",
        "unilateral_modification_clause",
        "automatic_acceleration_clause",
        "disproportionate_late_fee",
        "prepayment_penalty_clause",
        "notary_designation_clause",
        "mandatory_arbitration",
        "forced_jurisdiction_clause",
    }
)


def test_elements_detected_default_all_false():
    instance = ElementsDetected()
    for key in EXPECTED_ELEMENT_KEYS:
        assert getattr(instance, key) is False


def test_elements_detected_keys_are_closed():
    """Schema exposes exactly the 11 PRD §US-05 flags — no drift."""
    assert frozenset(ElementsDetected.model_fields.keys()) == EXPECTED_ELEMENT_KEYS


def test_elements_detected_rejects_unknown_keys():
    with pytest.raises(ValidationError):
        ElementsDetected.model_validate({"public_deed": True, "fake_clause": True})


# ---------------------------------------------------------------------------
# IndicatorsFound — list coercion + caps (CS-114 AC4)
# ---------------------------------------------------------------------------


def test_indicators_found_coerces_bare_list():
    found = IndicatorsFound.model_validate(["compraventa con saldo a plazos", "precio en USD"])
    assert found.items == ("compraventa con saldo a plazos", "precio en USD")
    assert len(found) == 2


def test_indicators_found_default_empty():
    found = IndicatorsFound()
    assert found.items == ()
    assert len(found) == 0


def test_indicators_found_rejects_blank_entry():
    with pytest.raises(ValidationError):
        IndicatorsFound.model_validate(["   "])


def test_indicators_found_rejects_over_cap():
    payload = [f"indicator {i}" for i in range(MAX_INDICATORS + 1)]
    with pytest.raises(ValidationError):
        IndicatorsFound.model_validate(payload)


def test_indicators_found_rejects_over_length():
    with pytest.raises(ValidationError):
        IndicatorsFound.model_validate(["x" * (MAX_INDICATOR_LENGTH + 1)])


# ---------------------------------------------------------------------------
# ClassificationResult — envelope wiring (CS-110 + CS-114)
# ---------------------------------------------------------------------------


def test_classification_result_defaults_for_legacy_payload():
    """Legacy CS-110 payload (no new keys) still validates with safe defaults."""
    result = ClassificationResult.model_validate({"contract_type": "CVP", "confidence": 0.9})
    assert result.classification_attempts == 1
    assert result.indicators_found.items == ()
    assert result.elements_detected.public_deed is False


def test_classification_result_attempts_capped():
    with pytest.raises(ValidationError):
        ClassificationResult(contract_type=ContractType.CVP, confidence=0.9, classification_attempts=4)
    with pytest.raises(ValidationError):
        ClassificationResult(contract_type=ContractType.CVP, confidence=0.9, classification_attempts=0)


def test_classification_result_consumes_full_llm_shape():
    """End-to-end LLM-shaped payload validates as PRD F2 §8.1 specifies."""
    payload = {
        "contract_type": "CVP",
        "confidence": 0.92,
        "reasoning": "se identifica precio + cuotas",
        "classification_attempts": 1,
        "indicators_found": ["precio explícito", "saldo a plazos"],
        "elements_detected": {
            "public_deed": True,
            "arbitration_clause": False,
        },
    }
    result = ClassificationResult.model_validate(payload)
    assert result.contract_type is ContractType.CVP
    assert result.indicators_found.items == ("precio explícito", "saldo a plazos")
    assert result.elements_detected.public_deed is True
    # Defaults stick for keys the LLM did not surface.
    assert result.elements_detected.arbitration_clause is False
    assert result.elements_detected.warranty_exemption_clause is False


# ---------------------------------------------------------------------------
# ContractExtraction — field_confidences key validator (CS-114)
# ---------------------------------------------------------------------------


def test_contract_extraction_rejects_unknown_confidence_key():
    """Typos in `field_confidences` keys are rejected to prevent silent drift."""
    with pytest.raises(ValidationError):
        ContractExtraction(
            contract_type=ContractType.CVP,
            field_confidences={"purchase_price_usd_typo": ConfidenceBand.from_score(0.9)},
        )
