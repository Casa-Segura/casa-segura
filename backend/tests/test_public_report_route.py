"""Public HTML stub route."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from platform_core.domain.enums import DeliveryStatus
from tests.factories import ContractAnalysisFactory


@pytest.mark.django_db
def test_public_report_returns_html_when_link_ready():
    analysis = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.AVAILABLE_LINK.value,
        link_expires_at=timezone.now() + timedelta(days=1),
    )
    c = Client()
    resp = c.get(f"/r/{analysis.public_short_id}/")
    assert resp.status_code == 200
    assert b"Casa Segura" in resp.content


@pytest.mark.django_db
def test_public_report_expired_returns_410():
    analysis = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.AVAILABLE_LINK.value,
        link_expires_at=timezone.now() - timedelta(days=1),
    )
    c = Client()
    resp = c.get(f"/r/{analysis.public_short_id}/")
    assert resp.status_code == 410
