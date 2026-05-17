"""CS-242 — SMS provider callback HTTP surface."""

from __future__ import annotations

import hashlib
import hmac
import json

import pytest
from rest_framework.test import APIClient

from django.test import override_settings
from django.utils import timezone

from delivery.domain.enums import DeliveryRequestStatus
from tests.factories import ContractAnalysisFactory, DeliveryRequestFactory


def _sign(secret: str, raw: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


@pytest.mark.django_db
def test_sms_webhook_rejects_bad_hmac():
    client = APIClient()
    body = json.dumps({"event": "delivered", "provider_message_id": "mid"}).encode()
    with override_settings(SMS_WEBHOOK_SECRET="sec"):
        resp = client.post(
            "/api/v1/webhooks/sms/",
            data=body,
            content_type="application/json",
            HTTP_X_SMS_SIGNATURE="deadbeef",
        )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_sms_webhook_marks_delivered():
    analysis = ContractAnalysisFactory()
    dr = DeliveryRequestFactory(
        analysis=analysis,
        channel="sms_summary",
        provider_message_id="sms_mid_1",
        status=DeliveryRequestStatus.SENDING.value,
    )

    client = APIClient()
    body = json.dumps(
        {"event": "message.delivered", "provider_message_id": "sms_mid_1"},
    ).encode()
    secret = "sms_wh_sec"
    sig = _sign(secret, body)

    with override_settings(SMS_WEBHOOK_SECRET=secret):
        resp = client.post(
            "/api/v1/webhooks/sms/",
            data=body,
            content_type="application/json",
            HTTP_X_SMS_SIGNATURE=sig,
        )

    assert resp.status_code == 200
    dr.refresh_from_db()
    assert dr.status == DeliveryRequestStatus.DELIVERED.value
    assert dr.delivered_at is not None


@pytest.mark.django_db
def test_sms_webhook_delivered_idempotent():
    analysis = ContractAnalysisFactory()
    at = timezone.now()
    dr = DeliveryRequestFactory(
        analysis=analysis,
        channel="sms_summary",
        provider_message_id="sms_mid_2",
        status=DeliveryRequestStatus.DELIVERED.value,
        delivered_at=at,
    )

    client = APIClient()
    body = json.dumps({"event": "delivered", "provider_message_id": "sms_mid_2"}).encode()
    secret = "sms_wh_sec2"
    sig = _sign(secret, body)

    with override_settings(SMS_WEBHOOK_SECRET=secret):
        resp = client.post(
            "/api/v1/webhooks/sms/",
            data=body,
            content_type="application/json",
            HTTP_X_SMS_SIGNATURE=sig,
        )

    assert resp.status_code == 200
    dr.refresh_from_db()
    assert dr.delivered_at == at
