"""CS-248 — guarded resend HTTP contract."""

from __future__ import annotations

from datetime import timedelta

import pytest
from rest_framework.test import APIClient

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from delivery.application.target_hash import hash_delivery_target
from delivery.infrastructure.django.models import DeliveryRequest
from platform_core.domain.enums import DeliveryChannel
from tests.factories import ContractAnalysisFactory


@pytest.mark.django_db
def test_resend_202_increments_count_and_enqueues_resend_row():
    email = "Pat.User@Example.com"
    with override_settings(DELIVERY_TARGET_HASH_SALT="testsalt-resend"):
        digest = hash_delivery_target(email)
        analysis = ContractAnalysisFactory(
            delivery_channel=DeliveryChannel.EMAIL_PDF.value,
            delivery_target_hash=digest,
            link_expires_at=timezone.now() + timedelta(days=7),
            resend_count=0,
        )

    client = APIClient()
    url = reverse("v1:delivery-resend", kwargs={"public_short_id": analysis.public_short_id})
    with override_settings(DELIVERY_TARGET_HASH_SALT="testsalt-resend"):
        resp = client.post(url, {"target": "pat.user@example.com"}, format="json")

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "accepted"
    assert body["channel"] == DeliveryChannel.EMAIL_PDF.value

    analysis.refresh_from_db()
    assert analysis.resend_count == 1
    assert DeliveryRequest.objects.filter(analysis_id=analysis.pk, is_resend=True).count() == 1


@pytest.mark.django_db
def test_resend_target_mismatch_403():
    with override_settings(DELIVERY_TARGET_HASH_SALT="testsalt-resend"):
        digest = hash_delivery_target("good@example.com")
        analysis = ContractAnalysisFactory(
            delivery_channel=DeliveryChannel.EMAIL_PDF.value,
            delivery_target_hash=digest,
            link_expires_at=timezone.now() + timedelta(days=7),
            resend_count=0,
        )

    client = APIClient()
    url = reverse("v1:delivery-resend", kwargs={"public_short_id": analysis.public_short_id})
    with override_settings(DELIVERY_TARGET_HASH_SALT="testsalt-resend"):
        resp = client.post(url, {"target": "other@example.com"}, format="json")

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "TARGET_MISMATCH"


@pytest.mark.django_db
def test_resend_limit_429():
    phone = "+15550001111"
    with override_settings(DELIVERY_TARGET_HASH_SALT="testsalt-resend"):
        digest = hash_delivery_target(phone)
        analysis = ContractAnalysisFactory(
            delivery_channel=DeliveryChannel.SMS_SUMMARY.value,
            delivery_target_hash=digest,
            link_expires_at=timezone.now() + timedelta(days=7),
            resend_count=3,
        )

    client = APIClient()
    url = reverse("v1:delivery-resend", kwargs={"public_short_id": analysis.public_short_id})
    with override_settings(DELIVERY_TARGET_HASH_SALT="testsalt-resend"):
        resp = client.post(url, {"target": phone}, format="json")

    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "RESEND_LIMIT_EXCEEDED"


@pytest.mark.django_db
def test_resend_expired_link_410():
    with override_settings(DELIVERY_TARGET_HASH_SALT="testsalt-resend"):
        digest = hash_delivery_target("u@example.com")
        analysis = ContractAnalysisFactory(
            delivery_channel=DeliveryChannel.EMAIL_PDF.value,
            delivery_target_hash=digest,
            link_expires_at=timezone.now() - timedelta(days=1),
            resend_count=0,
        )

    client = APIClient()
    url = reverse("v1:delivery-resend", kwargs={"public_short_id": analysis.public_short_id})
    with override_settings(DELIVERY_TARGET_HASH_SALT="testsalt-resend"):
        resp = client.post(url, {"target": "u@example.com"}, format="json")

    assert resp.status_code == 410
    assert resp.json()["error"]["code"] == "LINK_EXPIRED"
