"""CS-110 — PRD F2 §US-01 confidence-band orchestration in ContractClassifier.

Covers AC2 (`confidence > 0.85` → accept), AC3 (`[0.65, 0.85]` → §8.3
validator → accept-or-NOT_CLASSIFIABLE), AC4 (`< 0.65` → NOT_CLASSIFIABLE
without retry), and the parse / transient / empty-input error envelope.

Rule 9 invariants tested:
    - `test_band_upper_boundary_is_strict`     — 0.85 ≠ accept (PRD §US-01)
    - `test_band_lower_boundary_is_inclusive`  — 0.65 → validator (PRD §US-01)
    - `test_parse_failure_distinct_from_not_classifiable`
"""

from __future__ import annotations

import json

import httpx
import pytest

from classification.application.classifier import (
    ClassificationError,
    ContractClassifier,
)
from classification.domain.contract_type import ContractType
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


def _stage_calls(router, *payloads: dict) -> object:
    """Stage one or more sequential chat-completion responses on `router`."""
    return router.post(CHAT_URL).mock(
        side_effect=[openrouter_response(p) for p in payloads],
    )


# ---------------------------------------------------------------------------
# Empty / transient input — error envelope
# ---------------------------------------------------------------------------


def test_empty_input_raises_typed_error(mock_openrouter):
    with ContractClassifier(client=_client()) as svc:
        with pytest.raises(ClassificationError) as exc:
            svc.classify("   ")
    assert exc.value.code == "EMPTY_INPUT"


def test_parse_failure_distinct_from_not_classifiable(mock_openrouter):
    """Rule 9: malformed LLM output is `LLM_PARSE_FAILED`, not `NOT_CLASSIFIABLE`."""
    mock_openrouter.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "this is not json"}}]},
        ),
    )
    with ContractClassifier(client=_client()) as svc:
        with pytest.raises(ClassificationError) as exc:
            svc.classify("texto del contrato")
    assert exc.value.code == "LLM_PARSE_FAILED"


def test_schema_violation_raises_parse_failed(mock_openrouter):
    """Unknown `contract_type` is a schema violation, not NOT_CLASSIFIABLE."""
    mock_openrouter.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"contract_type": "SUBLEASE", "confidence": 0.9},
                            ),
                        },
                    },
                ],
            },
        ),
    )
    with ContractClassifier(client=_client()) as svc:
        with pytest.raises(ClassificationError) as exc:
            svc.classify("texto")
    assert exc.value.code == "LLM_PARSE_FAILED"


# ---------------------------------------------------------------------------
# High-confidence band (>0.85) — accept primary, no validator
# ---------------------------------------------------------------------------


def test_high_confidence_accepts_primary(mock_openrouter):
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "CVP", "confidence": 0.92, "reasoning": "ok"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto del contrato")

    assert result.contract_type is ContractType.CVP
    assert result.classification_attempts == 1
    assert result.confidence == pytest.approx(0.92)
    assert route.call_count == 1  # validator not called


def test_band_upper_boundary_is_strict_0_851_accepts(mock_openrouter):
    """0.851 > 0.85 → accept with attempts=1, no validator call."""
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "CVP", "confidence": 0.851, "reasoning": "ok"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert result.classification_attempts == 1
    assert route.call_count == 1


# ---------------------------------------------------------------------------
# Medium band [0.65, 0.85] — validator runs
# ---------------------------------------------------------------------------


def test_band_upper_boundary_is_strict_0_850_triggers_validator(mock_openrouter):
    """Rule 9: 0.85 (not >0.85) routes through the §8.3 validator."""
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "CVP", "confidence": 0.85, "reasoning": "borderline"},
        {"contract_type": "CVP", "confidence": 0.88, "reasoning": "confirm"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert route.call_count == 2  # primary + validator
    assert result.contract_type is ContractType.CVP
    assert result.classification_attempts == 2
    # Validator's confidence is the one that lands on the envelope.
    assert result.confidence == pytest.approx(0.88)


def test_band_lower_boundary_is_inclusive_0_650_triggers_validator(mock_openrouter):
    """Rule 9: 0.65 lands inside the medium band per PRD F2 §US-01."""
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "CVP", "confidence": 0.65, "reasoning": "tight"},
        {"contract_type": "CVP", "confidence": 0.80, "reasoning": "still CVP"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert route.call_count == 2
    assert result.contract_type is ContractType.CVP
    assert result.classification_attempts == 2


def test_validator_disagreement_returns_not_classifiable(mock_openrouter):
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "CVP", "confidence": 0.75, "reasoning": "primary"},
        {"contract_type": "CVC", "confidence": 0.90, "reasoning": "actually cash"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert route.call_count == 2
    assert result.contract_type is ContractType.NOT_CLASSIFIABLE
    assert result.classification_attempts == 2


def test_validator_low_confidence_returns_not_classifiable(mock_openrouter):
    """Validator agrees on type but its confidence is in the low band itself."""
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "CVP", "confidence": 0.70, "reasoning": "ambivalent"},
        {"contract_type": "CVP", "confidence": 0.50, "reasoning": "unsure"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert route.call_count == 2
    assert result.contract_type is ContractType.NOT_CLASSIFIABLE
    assert result.classification_attempts == 2


def test_validator_threshold_is_strict_lower(mock_openrouter):
    """Validator confidence must be `> 0.65` (not `>= 0.65`) to confirm."""
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "CVP", "confidence": 0.70, "reasoning": "primary"},
        {"contract_type": "CVP", "confidence": 0.65, "reasoning": "exactly at floor"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert route.call_count == 2
    assert result.contract_type is ContractType.NOT_CLASSIFIABLE


# ---------------------------------------------------------------------------
# Low band (<0.65) — NOT_CLASSIFIABLE without validator
# ---------------------------------------------------------------------------


def test_band_lower_boundary_is_strict_0_649_rejects_without_retry(mock_openrouter):
    """Rule 9: 0.649 < 0.65 → NOT_CLASSIFIABLE immediately, attempts=1."""
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "CVP", "confidence": 0.649, "reasoning": "too weak"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert route.call_count == 1  # validator must NOT be called
    assert result.contract_type is ContractType.NOT_CLASSIFIABLE
    assert result.classification_attempts == 1


def test_low_confidence_path_does_not_call_validator(mock_openrouter):
    route = _stage_calls(
        mock_openrouter,
        {"contract_type": "ARV", "confidence": 0.40, "reasoning": "very weak"},
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert route.call_count == 1
    assert result.contract_type is ContractType.NOT_CLASSIFIABLE
    assert result.classification_attempts == 1


# ---------------------------------------------------------------------------
# Primary returns NOT_CLASSIFIABLE high-confidence — passthrough
# ---------------------------------------------------------------------------


def test_primary_not_classifiable_high_confidence_passthrough(mock_openrouter):
    """LLM is confident the doc is out-of-scope (PRD §US-06)."""
    route = _stage_calls(
        mock_openrouter,
        {
            "contract_type": "NOT_CLASSIFIABLE",
            "confidence": 0.95,
            "reasoning": "es una donación",
        },
    )
    with ContractClassifier(client=_client()) as svc:
        result = svc.classify("texto")

    assert route.call_count == 1
    assert result.contract_type is ContractType.NOT_CLASSIFIABLE
    assert result.classification_attempts == 1
