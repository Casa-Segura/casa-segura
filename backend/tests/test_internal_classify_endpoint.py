"""CS-110 PR-6 — `POST /api/v1/internal/classify` end-to-end.

Verifies the `IsInternal` permission contract, the request validation,
the orchestrator wiring, and the response envelope shape.
"""

from __future__ import annotations

import json

import httpx
import pytest
from rest_framework.test import APIClient

from django.urls import reverse

from conftest import OPENROUTER_BASE_URL, openrouter_response
from platform_core.infrastructure.django.models import ContractAnalysis
from shared.security.internal_auth import INTERNAL_TOKEN_HEADER
from tests.factories import CorpusVersionFactory, RubricVersionFactory

CHAT_URL = f"{OPENROUTER_BASE_URL}/chat/completions"

INTERNAL_TOKEN = "test-internal-token-rotate-me"
SUBMISSION_HASH = "b" * 64


def _classify_url() -> str:
    return reverse("v1_internal:classification:internal-classify")


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _configure_internal_token(settings):
    settings.INTERNAL_API_TOKEN = INTERNAL_TOKEN


@pytest.fixture
def active_catalog(db):
    rubric = RubricVersionFactory(version="1.0.0", is_active=True)
    corpus = CorpusVersionFactory(version="1.0.0", is_active=True)
    return rubric, corpus


def _stage_full_happy_chain(mock_openrouter):
    """Queue the four chat-completion responses one run of the pipeline needs."""
    return mock_openrouter.post(CHAT_URL).mock(
        side_effect=[
            openrouter_response(
                {
                    "contract_type": "CVP",
                    "confidence": 0.92,
                    "reasoning": "precio + cuotas",
                    "indicators_found": ["precio explícito"],
                    "elements_detected": {"public_deed": True},
                },
            ),
            openrouter_response(
                {
                    "mandatory_term": False,
                    "predefined_purchase_option": False,
                    "ownership_retained": False,
                    "taxes_to_buyer": False,
                    "risks_to_buyer": False,
                    "payments_as_rent": False,
                    "confidence": 0.7,
                    "reasoning": "no leasing",
                },
            ),
            openrouter_response({"project_name_raw": "Residencial Las Palmeras", "confidence": 0.95}),
            openrouter_response(
                {
                    "purchase_price_usd": {"value": 80000.0, "confidence": 0.92, "rationale": "precio"},
                    "down_payment_usd": {"value": 8000.0, "confidence": 0.9, "rationale": "prima"},
                    "down_payment_pct": {"value": 0.10, "confidence": 0.9, "rationale": "10%"},
                    "financed_amount_usd": {"value": 72000.0, "confidence": 0.9, "rationale": "saldo"},
                    "term_months": {"value": 72, "confidence": 0.95, "rationale": "72 meses"},
                    "monthly_payment_usd": {"value": 1167.0, "confidence": 0.85, "rationale": "cuota"},
                    "interest_rate_pct": {"value": 0.12, "confidence": 0.85, "rationale": "12% anual"},
                    "interest_calculation_base": {
                        "value": "outstanding_principal",
                        "confidence": 0.9,
                        "rationale": "saldo insoluto",
                    },
                    "payment_periodicity": {"value": "monthly", "confidence": 0.95, "rationale": "mensual"},
                },
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Auth contract — IsInternal
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_missing_token_returns_403(api_client, active_catalog):
    """No header at all — DRF surfaces 403 (the default for missing permission)."""
    response = api_client.post(
        _classify_url(),
        data={"submission_hash": SUBMISSION_HASH, "extracted_text": "texto"},
        format="json",
    )
    # DRF defaults to 401 for permission denial under anonymous auth (no
    # DEFAULT_AUTHENTICATION_CLASSES configured for this endpoint).
    assert response.status_code == 401


@pytest.mark.django_db
def test_wrong_token_returns_403(api_client, active_catalog):
    response = api_client.post(
        _classify_url(),
        data={"submission_hash": SUBMISSION_HASH, "extracted_text": "texto"},
        format="json",
        headers={INTERNAL_TOKEN_HEADER: "wrong-token"},
    )
    # DRF defaults to 401 for permission denial under anonymous auth (no
    # DEFAULT_AUTHENTICATION_CLASSES configured for this endpoint).
    assert response.status_code == 401


@pytest.mark.django_db
def test_unset_token_in_settings_fails_closed(api_client, active_catalog, settings):
    settings.INTERNAL_API_TOKEN = ""
    response = api_client.post(
        _classify_url(),
        data={"submission_hash": SUBMISSION_HASH, "extracted_text": "texto"},
        format="json",
        headers={INTERNAL_TOKEN_HEADER: ""},
    )
    # DRF defaults to 401 for permission denial under anonymous auth (no
    # DEFAULT_AUTHENTICATION_CLASSES configured for this endpoint).
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_missing_required_fields_returns_400(api_client, active_catalog):
    response = api_client.post(
        _classify_url(),
        data={"submission_hash": SUBMISSION_HASH},
        format="json",
        headers={INTERNAL_TOKEN_HEADER: INTERNAL_TOKEN},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Happy 200 — full envelope
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_happy_request_returns_full_envelope(api_client, mock_openrouter, active_catalog):
    _stage_full_happy_chain(mock_openrouter)

    response = api_client.post(
        _classify_url(),
        data={"submission_hash": SUBMISSION_HASH, "extracted_text": "texto sintético"},
        format="json",
        headers={INTERNAL_TOKEN_HEADER: INTERNAL_TOKEN},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["effective_contract_type"] == "CVP"
    assert body["was_created"] is True
    assert body["classification"]["contract_type"] == "CVP"
    assert body["classification"]["classification_attempts"] == 1
    assert body["leasing"]["should_reclassify"] is False
    assert body["leasing"]["severity"] == "none"
    assert "purchase_price_usd" in body["aggregated"]["slots"]
    assert ContractAnalysis.objects.filter(submission_hash=SUBMISSION_HASH).count() == 1


# ---------------------------------------------------------------------------
# Failed classification — 400 with typed error code
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_failed_classification_returns_400_with_code(api_client, mock_openrouter, active_catalog):
    mock_openrouter.post(CHAT_URL).mock(
        return_value=httpx.Response(
            200,
            json={"choices": [{"message": {"content": "this is not json"}}]},
        ),
    )

    response = api_client.post(
        _classify_url(),
        data={"submission_hash": SUBMISSION_HASH, "extracted_text": "texto"},
        format="json",
        headers={INTERNAL_TOKEN_HEADER: INTERNAL_TOKEN},
    )

    assert response.status_code == 400
    body = json.loads(response.content)
    assert body["error"]["code"] == "FAILED_CLASSIFICATION"
