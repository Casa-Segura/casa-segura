"""CS-111 — leasing reclassification detector + severity envelope.

Covers the AC band that PR-3 closes:
    - BR-02 / AC1: skip path for initial types outside {CVC, CVP, APV}.
    - §8.4 / AC2: detector executes on CVC / CVP / APV and parses both
      flat and nested JSON shapes.
    - AC3: ≥4 indicators → `recommended_type = LEA`, `should_reclassify`,
      `severity = high`.
    - AC4: 2-3 indicators -> warning envelope (severity low / medium) WITHOUT
      reclassification.
    - AC5: 0-1 indicators -> silent (severity none).

Rule 9 invariants:
    - `test_leasing_threshold_invariant_4_of_6` — flipping the BR-03 hinge
      from 4-of-6 to 3-of-6 breaks the test.
    - `test_severity_bucket_boundaries`         — count→severity mapping
      cannot drift silently.
"""

from __future__ import annotations

import json

import httpx
import pytest

from classification.application.classifier import ClassificationError
from classification.application.leasing_detector import (
    LeasingReclassificationDetector,
)
from classification.domain.contract_type import ContractType
from classification.domain.leasing_indicators import (
    DEFAULT_RECLASSIFICATION_THRESHOLD,
    LAF_INDICATOR_COUNT,
    LeasingIndicators,
)
from classification.domain.reclassification import (
    LeasingReclassificationResult,
    LeasingSeverity,
    severity_from_count,
)
from conftest import OPENROUTER_BASE_URL, openrouter_response
from shared.llm.openrouter import OpenRouterClient

CHAT_URL = f"{OPENROUTER_BASE_URL}/chat/completions"


def _client() -> OpenRouterClient:
    return OpenRouterClient(
        api_key="sk-or-v1-test",
        base_url=OPENROUTER_BASE_URL,
        timeout_seconds=5,
        max_retries=1,
        http_referer="https://test.local",
        x_title="Test",
    )


def _indicators(n_true: int) -> dict:
    """Build a §8.4 flat payload with the first `n_true` indicators set True."""
    keys = list(LeasingIndicators.model_fields.keys())
    if not (0 <= n_true <= LAF_INDICATOR_COUNT):
        raise ValueError(f"n_true must be in [0, {LAF_INDICATOR_COUNT}]; got {n_true}")
    return {key: idx < n_true for idx, key in enumerate(keys)}


# ---------------------------------------------------------------------------
# severity_from_count — pure mapping (Rule 9)
# ---------------------------------------------------------------------------


def test_severity_bucket_boundaries():
    """Each count maps to exactly one bucket; boundaries are explicit."""
    assert severity_from_count(0) is LeasingSeverity.NONE
    assert severity_from_count(1) is LeasingSeverity.NONE
    assert severity_from_count(2) is LeasingSeverity.LOW
    assert severity_from_count(3) is LeasingSeverity.MEDIUM
    assert severity_from_count(4) is LeasingSeverity.HIGH
    assert severity_from_count(5) is LeasingSeverity.HIGH
    assert severity_from_count(6) is LeasingSeverity.HIGH


def test_severity_aligns_with_reclassification_threshold():
    """Rule 9: severity HIGH MUST coincide with `is_leasing(threshold=4)`."""
    for n in range(LAF_INDICATOR_COUNT + 1):
        is_high = severity_from_count(n) is LeasingSeverity.HIGH
        crosses_threshold = n >= DEFAULT_RECLASSIFICATION_THRESHOLD
        assert is_high == crosses_threshold


def test_severity_rejects_negative_count():
    with pytest.raises(ValueError):
        severity_from_count(-1)


# ---------------------------------------------------------------------------
# Skip path (BR-02 / AC1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "initial_type",
    [
        ContractType.ARV,
        ContractType.ARC,
        ContractType.IVU,
        ContractType.FSV,
        ContractType.LEA,
        ContractType.NOT_CLASSIFIABLE,
    ],
)
def test_skip_path_returns_zero_indicator_envelope(mock_openrouter, initial_type):
    """Initial types outside {CVC, CVP, APV} short-circuit; no LLM call."""
    route = mock_openrouter.post(CHAT_URL).mock(return_value=httpx.Response(500))
    with LeasingReclassificationDetector(client=_client()) as svc:
        result = svc.detect("texto del contrato", initial_type=initial_type)

    assert route.call_count == 0
    assert result.original_type is initial_type
    assert result.recommended_type is initial_type
    assert result.should_reclassify is False
    assert result.indicators.total_indicators_found == 0
    assert result.severity is LeasingSeverity.NONE
    assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Reclassification path (AC3) — Rule 9: 4-of-6 threshold
# ---------------------------------------------------------------------------


def test_leasing_threshold_invariant_4_of_6(mock_openrouter):
    """Rule 9: 4 indicators → LEA; flipping the BR-03 hinge breaks this."""
    payload = {**_indicators(4), "confidence": 0.9, "reasoning": "ok"}
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with LeasingReclassificationDetector(client=_client()) as svc:
        result = svc.detect("texto", initial_type=ContractType.CVP)

    assert result.original_type is ContractType.CVP
    assert result.recommended_type is ContractType.LEA
    assert result.should_reclassify is True
    assert result.indicators.total_indicators_found == 4
    assert result.severity is LeasingSeverity.HIGH


def test_three_indicators_does_not_reclassify(mock_openrouter):
    """BVA: 3 indicators → keep CVP, severity=medium (warning artifact)."""
    payload = {**_indicators(3), "confidence": 0.85, "reasoning": "borderline"}
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with LeasingReclassificationDetector(client=_client()) as svc:
        result = svc.detect("texto", initial_type=ContractType.CVP)

    assert result.recommended_type is ContractType.CVP
    assert result.should_reclassify is False
    assert result.severity is LeasingSeverity.MEDIUM


def test_two_indicators_emits_low_severity_warning(mock_openrouter):
    payload = {**_indicators(2), "confidence": 0.7, "reasoning": "low warning"}
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with LeasingReclassificationDetector(client=_client()) as svc:
        result = svc.detect("texto", initial_type=ContractType.CVP)

    assert result.should_reclassify is False
    assert result.severity is LeasingSeverity.LOW


@pytest.mark.parametrize("n", [0, 1])
def test_zero_or_one_indicator_is_silent(mock_openrouter, n):
    payload = {**_indicators(n), "confidence": 0.3, "reasoning": "silent"}
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with LeasingReclassificationDetector(client=_client()) as svc:
        result = svc.detect("texto", initial_type=ContractType.CVP)

    assert result.should_reclassify is False
    assert result.severity is LeasingSeverity.NONE


# ---------------------------------------------------------------------------
# Parser tolerance (PRD §8.4 flat or nested)
# ---------------------------------------------------------------------------


def test_parser_accepts_nested_leasing_indicators_shape(mock_openrouter):
    """§8.4 reference shape: `leasing_indicators: {field: {detected, evidence}}`."""
    nested = {
        "leasing_indicators": {
            key: {"detected": True, "evidence": "n/a"}
            for key in list(LeasingIndicators.model_fields.keys())[:4]
        },
        "confidence": 0.88,
        "reasoning": "matches Art. 2",
    }
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(nested))

    with LeasingReclassificationDetector(client=_client()) as svc:
        result = svc.detect("texto", initial_type=ContractType.CVP)

    assert result.indicators.total_indicators_found == 4
    assert result.should_reclassify is True


def test_parser_rejects_non_json_payload(mock_openrouter):
    mock_openrouter.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not json"}}]},
        ),
    )
    with LeasingReclassificationDetector(client=_client()) as svc:
        with pytest.raises(ClassificationError) as exc:
            svc.detect("texto", initial_type=ContractType.CVP)
    assert exc.value.code == "LLM_PARSE_FAILED"


def test_parser_rejects_payload_that_is_not_an_object(mock_openrouter):
    mock_openrouter.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps([1, 2, 3])}}]},
        ),
    )
    with LeasingReclassificationDetector(client=_client()) as svc:
        with pytest.raises(ClassificationError) as exc:
            svc.detect("texto", initial_type=ContractType.CVP)
    assert exc.value.code == "LLM_PARSE_FAILED"


# ---------------------------------------------------------------------------
# LeasingReclassificationResult — validators
# ---------------------------------------------------------------------------


def test_envelope_severity_computed_from_indicators():
    """Construct directly to verify the computed property without an LLM call."""
    indicators = LeasingIndicators(
        mandatory_term=True,
        predefined_purchase_option=True,
        ownership_retained=True,
        taxes_to_buyer=True,
        risks_to_buyer=False,
        payments_as_rent=False,
    )
    result = LeasingReclassificationResult(
        original_type=ContractType.CVP,
        recommended_type=ContractType.LEA,
        should_reclassify=True,
        indicators=indicators,
        confidence=0.9,
        reasoning="four-of-six",
    )
    assert result.severity is LeasingSeverity.HIGH
    assert result.indicators.total_indicators_found == 4


def test_envelope_rejects_inconsistent_reclassify_flag():
    """should_reclassify must equal (recommended_type != original_type)."""
    with pytest.raises(ValueError):
        LeasingReclassificationResult(
            original_type=ContractType.CVP,
            recommended_type=ContractType.CVP,
            should_reclassify=True,  # inconsistent
            indicators=LeasingIndicators(),
            confidence=0.5,
        )
