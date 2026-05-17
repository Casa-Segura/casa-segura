"""Public TTL HTML report route (CS-247 / canonical F6 renderer)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from django.test import Client
from django.utils import timezone

from delivery.application.report_html import generate_report_html_for_analysis
from ingestion.domain.enums import ProcessingStatus
from platform_core.domain.enums import DeliveryStatus
from tests.factories import ContractAnalysisFactory, ContractSubmissionFactory


@pytest.mark.django_db
def test_public_report_returns_html_when_link_ready():
    analysis = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.AVAILABLE_LINK.value,
        link_expires_at=timezone.now() + timedelta(days=1),
    )
    c = Client()
    resp = c.get(f"/r/{analysis.public_short_id}/")
    assert resp.status_code == 200
    body = resp.content
    assert analysis.public_short_id.encode() in body
    assert "Análisis de Contrato Casa Segura".encode() in body
    assert b'class="cs-footer"' in body
    assert "Hash del análisis".encode() in body
    assert b"Vista regenerada bajo demanda" not in body
    assert resp["Cache-Control"] == "no-store"
    assert "noindex" in resp["X-Robots-Tag"]


@pytest.mark.django_db
def test_public_report_pending_submission_returns_404():
    analysis = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.AVAILABLE_LINK.value,
        link_expires_at=timezone.now() + timedelta(days=1),
    )
    ContractSubmissionFactory(analysis=analysis, processing_status=ProcessingStatus.RECEIVED.value)
    c = Client()
    resp = c.get(f"/r/{analysis.public_short_id}/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_generate_report_html_for_analysis_returns_canonical_template():
    analysis = ContractAnalysisFactory()
    html, stats = generate_report_html_for_analysis(
        public_short_id=analysis.public_short_id,
        analysis=analysis,
    )
    assert "Análisis de Contrato Casa Segura" in html
    assert 'class="cs-footer"' in html
    assert stats.byte_length == len(html.encode())


@pytest.mark.django_db
def test_public_report_expired_returns_410():
    analysis = ContractAnalysisFactory(
        delivery_status=DeliveryStatus.AVAILABLE_LINK.value,
        link_expires_at=timezone.now() - timedelta(days=1),
    )
    c = Client()
    resp = c.get(f"/r/{analysis.public_short_id}/")
    assert resp.status_code == 410
    assert analysis.public_short_id.encode() not in resp.content
    assert resp["Cache-Control"] == "no-store"
