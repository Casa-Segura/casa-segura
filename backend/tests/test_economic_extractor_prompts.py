"""CS-113 PR-5 — golden tests for `EconomicFieldExtractor` + AMBIGUOUS signal.

Covers the behavioural contracts the orchestrator (PR-6) and CS-116
aggregator depend on:

    - Monthly-only rate -> the extractor accepts both `monthly_rate_pct`
      and `interest_rate_pct` derived via `(1+m)^12 - 1`. The compounding
      is enforced at the prompt level; this test asserts the prompt text
      carries the formula verbatim (Rule 9 -- silent `r*12` linearization
      would break the test).
    - Conflicting figures -> the extractor surfaces the field via
      `ambiguous_fields` rather than substituting null (PRD F5 BR-09).
    - Absent field -> `not_present` semantics (no value, status falls
      through to NOT_PRESENT in CS-116).
    - Saldo total -> `interest_calculation_base="total_balance"`
      precursor is wired through to CS-116's
      `interest_calculation_base_unfavorable` warning.
    - NOT_CLASSIFIABLE short-circuit -> no LLM call.
"""

from __future__ import annotations

import json

import httpx
import pytest

from classification.application.economic_extractor import EconomicFieldExtractor
from classification.application.economic_prompts import _BASE_PRELUDE, build_messages
from classification.application.errors import EconomicExtractionError
from classification.application.extraction_aggregator import (
    WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE,
    aggregate_extraction,
)
from classification.domain.contract_type import ContractType
from classification.domain.extraction_status import ExtractionStatus
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


# ---------------------------------------------------------------------------
# Rule 9 — monthly compounding invariant (prompt-level)
# ---------------------------------------------------------------------------


def test_monthly_compounding_invariant():
    """PR-5 Rule 9: silent `r*12` linearization is a regulatory bug.

    The §8.5 prompt must instruct the LLM to derive the annual effective
    rate via `(1+mensual)^12 - 1`. If anybody changes the prompt to a
    naive multiplication, the test rejects the change at PR review time.
    """
    assert "(1 + mensual)^12 - 1" in _BASE_PRELUDE
    # Negative invariant: the naive shape must NOT appear.
    assert "mensual * 12" not in _BASE_PRELUDE


def test_prompt_routes_ambiguous_to_explicit_status():
    """The LLM must be told to emit `extraction_status="ambiguous"` on conflict."""
    assert "extraction_status" in _BASE_PRELUDE
    assert "ambiguous" in _BASE_PRELUDE


def test_build_messages_returns_system_user_pair():
    messages = build_messages("texto sintético", ContractType.CVP)
    assert [m["role"] for m in messages] == ["system", "user"]
    assert "texto sintético" in messages[1]["content"]


# ---------------------------------------------------------------------------
# Happy path — monthly rate + saldo total triggers precursor
# ---------------------------------------------------------------------------


def test_monthly_only_rate_carries_both_rates(mock_openrouter):
    """LLM returns monthly + annual derived; both reach the extraction model."""
    payload = {
        "purchase_price_usd": {"value": 80000.0, "confidence": 0.92, "rationale": "precio total"},
        "down_payment_usd": {"value": 8000.0, "confidence": 0.9, "rationale": "prima"},
        "down_payment_pct": {"value": 0.10, "confidence": 0.9, "rationale": "10%"},
        "financed_amount_usd": {"value": 72000.0, "confidence": 0.9, "rationale": "saldo"},
        "term_months": {"value": 72, "confidence": 0.95, "rationale": "72 meses"},
        "monthly_rate_pct": {"value": 0.0125, "confidence": 0.85, "rationale": "1.25% mensual"},
        "interest_rate_pct": {
            "value": 0.16075452,  # (1.0125)^12 - 1 ≈ 0.16075
            "confidence": 0.85,
            "rationale": "anual = (1+mensual)^12 - 1 = 0.16075",
        },
        "monthly_payment_usd": {"value": 1167.13, "confidence": 0.85, "rationale": "cuota"},
        "interest_calculation_base": {
            "value": "outstanding_principal",
            "confidence": 0.9,
            "rationale": "saldo insoluto",
        },
        "payment_periodicity": {"value": "monthly", "confidence": 0.95, "rationale": "mensual"},
    }
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with EconomicFieldExtractor(client=_client()) as svc:
        extraction = svc.extract("texto", ContractType.CVP)

    assert extraction.extracted_fields.monthly_rate_pct == pytest.approx(0.0125)
    assert extraction.extracted_fields.interest_rate_pct == pytest.approx(0.16075452)
    assert extraction.ambiguous_fields == []
    assert "monthly_rate_pct" in extraction.field_confidences
    assert "interest_rate_pct" in extraction.field_confidences


def test_saldo_total_triggers_unfavorable_precursor_when_rate_missing(mock_openrouter):
    """`interest_calculation_base=total_balance` + missing rate -> precursor fires."""
    payload = {
        "purchase_price_usd": {"value": 60000.0, "confidence": 0.9, "rationale": "precio"},
        "down_payment_usd": {"value": 6000.0, "confidence": 0.9, "rationale": "prima"},
        "down_payment_pct": {"value": 0.10, "confidence": 0.9, "rationale": "10%"},
        "financed_amount_usd": {"value": 54000.0, "confidence": 0.9, "rationale": "saldo"},
        "term_months": {"value": 60, "confidence": 0.9, "rationale": "60 meses"},
        "monthly_payment_usd": {"value": 1200.0, "confidence": 0.85, "rationale": "cuota"},
        "interest_calculation_base": {
            "value": "total_balance",
            "confidence": 0.9,
            "rationale": "intereses sobre saldo total",
        },
        "payment_periodicity": {"value": "monthly", "confidence": 0.95, "rationale": "mensual"},
        # Rate fields intentionally absent — PRD F5 §6 precursor for Art. 12 LPC.
        "monthly_rate_pct": {"value": None, "confidence": 0.0, "rationale": "no declarada"},
        "interest_rate_pct": {"value": None, "confidence": 0.0, "rationale": "no declarada"},
    }
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with EconomicFieldExtractor(client=_client()) as svc:
        extraction = svc.extract("texto", ContractType.CVP)
    aggregated = aggregate_extraction(extraction)

    assert extraction.extracted_fields.interest_calculation_base == "total_balance"
    assert WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE in aggregated.warning_precursors


# ---------------------------------------------------------------------------
# AMBIGUOUS path (PR-5 contract for CS-116)
# ---------------------------------------------------------------------------


def test_conflicting_figures_route_through_ambiguous_fields(mock_openrouter):
    """LLM emits `extraction_status=ambiguous` -> field lands in `ambiguous_fields`.

    The aggregator then maps the slot to `ExtractionStatus.AMBIGUOUS` so
    EPIC-05 / EPIC-06 see the explicit ambiguity rather than treating the
    missing value as "not present".
    """
    payload = {
        "purchase_price_usd": {"value": 80000.0, "confidence": 0.92, "rationale": "precio"},
        "monthly_payment_usd": {
            "value": None,
            "confidence": 0.0,
            "rationale": "dos cifras: USD 1,200 y USD 1,500 — no se elige",
            "extraction_status": "ambiguous",
        },
        "down_payment_usd": {"value": 8000.0, "confidence": 0.9, "rationale": "prima"},
        "down_payment_pct": {"value": 0.10, "confidence": 0.9, "rationale": "10%"},
        "financed_amount_usd": {"value": 72000.0, "confidence": 0.9, "rationale": "saldo"},
        "term_months": {"value": 60, "confidence": 0.9, "rationale": "60 meses"},
        "interest_rate_pct": {"value": 0.12, "confidence": 0.85, "rationale": "12% anual"},
        "interest_calculation_base": {
            "value": "outstanding_principal",
            "confidence": 0.9,
            "rationale": "saldo insoluto",
        },
        "payment_periodicity": {"value": "monthly", "confidence": 0.9, "rationale": "mensual"},
    }
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with EconomicFieldExtractor(client=_client()) as svc:
        extraction = svc.extract("texto", ContractType.CVP)

    assert "monthly_payment_usd" in extraction.ambiguous_fields
    # Value must be suppressed (BR-09 honesty: no silent fallback to a number).
    assert extraction.extracted_fields.monthly_payment_usd is None
    # And the ambiguity must NOT pollute the confidence map for that field.
    assert "monthly_payment_usd" not in extraction.field_confidences

    aggregated = aggregate_extraction(extraction)
    assert aggregated.slots["monthly_payment_usd"].status is ExtractionStatus.AMBIGUOUS
    assert aggregated.ambiguous_count == 1
    # AMBIGUOUS is NOT silently treated as PRESENT in `unverifiable_fields`.
    assert "monthly_payment_usd" in aggregated.unverifiable_fields


def test_ambiguous_takes_precedence_over_invalid(mock_openrouter):
    """If both demoted-invalid AND ambiguous-signal apply, AMBIGUOUS wins.

    Required field that the LLM flags `ambiguous` while also returning a
    null value must surface as AMBIGUOUS — the consumer needs to know the
    contract had conflicting data, not that it was simply missing.
    """
    payload = {
        "purchase_price_usd": {
            "value": None,
            "confidence": 0.0,
            "rationale": "dos cifras contradictorias",
            "extraction_status": "ambiguous",
        },
        "down_payment_usd": {"value": 8000.0, "confidence": 0.9, "rationale": "prima"},
        "down_payment_pct": {"value": 0.10, "confidence": 0.9, "rationale": "10%"},
        "financed_amount_usd": {"value": 72000.0, "confidence": 0.9, "rationale": "saldo"},
        "term_months": {"value": 60, "confidence": 0.9, "rationale": "60 meses"},
        "monthly_payment_usd": {"value": 1200.0, "confidence": 0.85, "rationale": "cuota"},
        "interest_rate_pct": {"value": 0.12, "confidence": 0.85, "rationale": "12% anual"},
        "interest_calculation_base": {
            "value": "outstanding_principal",
            "confidence": 0.9,
            "rationale": "saldo insoluto",
        },
        "payment_periodicity": {"value": "monthly", "confidence": 0.9, "rationale": "mensual"},
    }
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with EconomicFieldExtractor(client=_client()) as svc:
        extraction = svc.extract("texto", ContractType.CVP)
    aggregated = aggregate_extraction(extraction)

    assert "purchase_price_usd" in extraction.ambiguous_fields
    assert aggregated.slots["purchase_price_usd"].status is ExtractionStatus.AMBIGUOUS


# ---------------------------------------------------------------------------
# Absent / not_present path
# ---------------------------------------------------------------------------


def test_missing_required_field_routes_to_invalid_not_ambiguous(mock_openrouter):
    """LLM returns `null` for a required field with no ambiguity flag.

    `interest_rate_pct` is required for CVP, so the aggregator routes the
    missing value to `INVALID` via `classify_unverifiable`. The key
    invariant here is that absence WITHOUT an `extraction_status=ambiguous`
    signal MUST NOT bleed into `ambiguous_fields` — otherwise CS-116 would
    over-report ambiguity and EPIC-05 would treat absent data as conflict.
    """
    payload = {
        "purchase_price_usd": {"value": 80000.0, "confidence": 0.92, "rationale": "precio"},
        "down_payment_usd": {"value": 8000.0, "confidence": 0.9, "rationale": "prima"},
        "down_payment_pct": {"value": 0.10, "confidence": 0.9, "rationale": "10%"},
        "financed_amount_usd": {"value": 72000.0, "confidence": 0.9, "rationale": "saldo"},
        "term_months": {"value": 60, "confidence": 0.9, "rationale": "60 meses"},
        "monthly_payment_usd": {"value": 1200.0, "confidence": 0.85, "rationale": "cuota"},
        "interest_rate_pct": {"value": None, "confidence": 0.0, "rationale": "no declarada"},
        "interest_calculation_base": {"value": "unspecified", "confidence": 0.5, "rationale": "no especificado"},
        "payment_periodicity": {"value": "monthly", "confidence": 0.9, "rationale": "mensual"},
    }
    mock_openrouter.post(CHAT_URL).mock(return_value=openrouter_response(payload))

    with EconomicFieldExtractor(client=_client()) as svc:
        extraction = svc.extract("texto", ContractType.CVP)
    aggregated = aggregate_extraction(extraction)

    assert "interest_rate_pct" not in extraction.ambiguous_fields
    # CS-116 precedence: required-but-missing -> INVALID (not AMBIGUOUS).
    assert aggregated.slots["interest_rate_pct"].status is ExtractionStatus.INVALID
    assert aggregated.ambiguous_count == 0


# ---------------------------------------------------------------------------
# NOT_CLASSIFIABLE short-circuit + error envelope
# ---------------------------------------------------------------------------


def test_not_classifiable_short_circuits_without_llm_call(mock_openrouter):
    route = mock_openrouter.post(CHAT_URL).mock(return_value=httpx.Response(500))

    with EconomicFieldExtractor(client=_client()) as svc:
        extraction = svc.extract("texto", ContractType.NOT_CLASSIFIABLE)

    assert route.call_count == 0
    assert extraction.ambiguous_fields == []
    assert extraction.unverifiable_fields == []


def test_parse_failure_raises_typed_error(mock_openrouter):
    mock_openrouter.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not json"}}]},
        ),
    )
    with EconomicFieldExtractor(client=_client()) as svc:
        with pytest.raises(EconomicExtractionError) as exc:
            svc.extract("texto", ContractType.CVP)
    assert exc.value.code == "LLM_PARSE_FAILED"


def test_payload_not_object_raises_typed_error(mock_openrouter):
    mock_openrouter.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": json.dumps([1, 2, 3])}}]},
        ),
    )
    with EconomicFieldExtractor(client=_client()) as svc:
        with pytest.raises(EconomicExtractionError) as exc:
            svc.extract("texto", ContractType.CVP)
    assert exc.value.code == "LLM_PARSE_FAILED"
