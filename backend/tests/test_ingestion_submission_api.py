"""CS-058 — submission upload API disclaimer enforcement."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from ingestion.application.ocr.errors import ExtractionResult
from ingestion.domain.enums import DisclaimerAcceptanceMethod


def _tiny_pdf() -> SimpleUploadedFile:
    body = (
        b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"
    )
    return SimpleUploadedFile("c.pdf", body, content_type="application/pdf")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_missing_disclaimer_returns_disclaimer_required_envelope(api_client):
    pdf = _tiny_pdf()
    resp = api_client.post(
        "/api/v1/submissions/",
        {"file": pdf},
        format="multipart",
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "DISCLAIMER_REQUIRED"
    assert body["schema_version"]
    assert "correlation_id" in body


@pytest.mark.django_db
def test_false_disclaimer_returns_disclaimer_required(api_client):
    pdf = _tiny_pdf()
    resp = api_client.post(
        "/api/v1/submissions/",
        {
            "file": pdf,
            "disclaimer_accepted": "false",
            "disclaimer_method": DisclaimerAcceptanceMethod.CHECKBOX.value,
            "source": "web",
        },
        format="multipart",
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "DISCLAIMER_REQUIRED"


@pytest.mark.django_db
def test_no_submission_row_when_disclaimer_missing(api_client):
    from ingestion.infrastructure.django.models import ContractSubmission

    pdf = _tiny_pdf()
    api_client.post("/api/v1/submissions/", {"file": pdf}, format="multipart")
    assert ContractSubmission.objects.count() == 0


@pytest.mark.django_db
def test_bogus_disclaimer_method_validation_error(api_client):
    pdf = _tiny_pdf()
    resp = api_client.post(
        "/api/v1/submissions/",
        {
            "file": pdf,
            "disclaimer_accepted": "true",
            "disclaimer_method": "not_a_real_method",
        },
        format="multipart",
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "validation_error"


@pytest.mark.django_db
def test_bogus_disclaimer_acceptance_method_alias_validation_error(api_client):
    pdf = _tiny_pdf()
    resp = api_client.post(
        "/api/v1/submissions/",
        {
            "file": pdf,
            "disclaimer_accepted": "true",
            "disclaimer_acceptance_method": "telegram_smoke_signal",
        },
        format="multipart",
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "validation_error"


@pytest.mark.django_db
def test_success_sets_disclaimer_accepted_at(settings, api_client):
    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    pdf = _tiny_pdf()
    before = timezone.now()
    fake_extract = ExtractionResult(
        text="texto de prueba en español suficiente",
        token_count=10,
        language="es",
        page_count=1,
    )
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=fake_extract,
    ):
        resp = api_client.post(
            "/api/v1/submissions/",
            {
                "file": pdf,
                "disclaimer_accepted": "true",
                "disclaimer_acceptance_method": DisclaimerAcceptanceMethod.CHECKBOX.value,
                "submission_source": "web",
            },
            format="multipart",
        )
    assert resp.status_code == 201, resp.content
    from ingestion.infrastructure.django.models import ContractSubmission

    sub = ContractSubmission.objects.get()
    assert sub.disclaimer_accepted_at is not None
    assert sub.disclaimer_accepted_at >= before
    assert sub.disclaimer_method == DisclaimerAcceptanceMethod.CHECKBOX.value
    assert timezone.is_aware(sub.disclaimer_accepted_at)
