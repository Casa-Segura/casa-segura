"""CS-056: language gate — 2000-char window + 0.85 confidence threshold + HTTP 422."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.upload_service import FileUpload, UploadRequest, ingest_upload  # noqa: F401
from ingestion.application.ocr.language import (
    LANGUAGE_DETECTION_WINDOW_CHARS,
    detect_language,
    ensure_spanish,
)
from ingestion.domain.enums import DisclaimerAcceptanceMethod, ProcessingStatus


# ─── Detector wiring: 2000-char window + detect_langs() ────────────────


@pytest.fixture
def patched_detect_langs():
    """Patch ``langdetect.detect_langs`` so we can assert what window is sent."""

    with patch("langdetect.detect_langs") as mock_detect:
        yield mock_detect


def _Lang(code: str, prob: float):  # noqa: N802 — match langdetect.Language shape
    return MagicMock(lang=code, prob=prob)


def test_detect_language_uses_first_2000_chars_only(patched_detect_langs):
    """PRD §US-08 first-2000-chars window: anything past the cutoff is ignored."""

    patched_detect_langs.return_value = [_Lang("es", 0.99)]
    long_text = "hola mundo " * 5000  # 55k chars
    code, prob = detect_language(long_text)
    args, _ = patched_detect_langs.call_args
    assert len(args[0]) == LANGUAGE_DETECTION_WINDOW_CHARS
    assert code == "es"
    assert prob == pytest.approx(0.99)


def test_ensure_spanish_at_0_851_no_warning(patched_detect_langs, caplog):
    """0.851 > 0.85 → continue without low-confidence warning."""

    patched_detect_langs.return_value = [_Lang("es", 0.851)]
    code = ensure_spanish("texto en español de prueba con suficiente longitud para pasar")
    assert code == "es"
    assert "ocr.language.low_confidence" not in caplog.text


def test_ensure_spanish_at_0_850_emits_warning(patched_detect_langs, caplog):
    """0.85 boundary → continue but log low-confidence warning (PRD §US-08 b3)."""

    patched_detect_langs.return_value = [_Lang("es", 0.850)]
    with caplog.at_level("WARNING"):
        code = ensure_spanish("texto en español de prueba con suficiente longitud para pasar")
    assert code == "es"
    assert "low_confidence" in caplog.text


def test_ensure_spanish_at_0_849_emits_warning(patched_detect_langs, caplog):
    """0.849 < 0.85 → continue with warning."""

    patched_detect_langs.return_value = [_Lang("es", 0.849)]
    with caplog.at_level("WARNING"):
        ensure_spanish("texto en español de prueba con suficiente longitud para pasar")
    assert "low_confidence" in caplog.text


def test_ensure_spanish_rejects_english_top(patched_detect_langs):
    """Non-Spanish top → REJECTED_LANGUAGE."""

    patched_detect_langs.return_value = [_Lang("en", 0.90)]
    with pytest.raises(NotAnalyzableError) as exc:
        ensure_spanish("this is english content of sufficient length to detect")
    assert exc.value.reason == NotAnalyzableReason.REJECTED_LANGUAGE


def test_detect_language_undetectable_below_min_chars():
    """Short text → LANGUAGE_UNDETECTABLE before invoking langdetect."""

    with pytest.raises(NotAnalyzableError) as exc:
        detect_language("hola")
    assert exc.value.reason == NotAnalyzableReason.LANGUAGE_UNDETECTABLE


# ─── API: rejected_language returns HTTP 422 LANGUAGE_NOT_SUPPORTED ────


def _tiny_pdf() -> SimpleUploadedFile:
    body = (
        b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"
    )
    return SimpleUploadedFile("c.pdf", body, content_type="application/pdf")


@pytest.mark.django_db
def test_rejected_language_returns_422_language_not_supported(settings):
    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    client = APIClient()
    pdf = _tiny_pdf()

    with patch(
        "ingestion.application.upload_service._run_extractor",
        side_effect=NotAnalyzableError(
            reason=NotAnalyzableReason.REJECTED_LANGUAGE,
            message="detected 'en' (p=0.900)",
        ),
    ):
        resp = client.post(
            "/api/v1/submissions/",
            {
                "file": pdf,
                "disclaimer_accepted": "true",
                "disclaimer_method": DisclaimerAcceptanceMethod.CHECKBOX.value,
            },
            format="multipart",
        )

    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "LANGUAGE_NOT_SUPPORTED"
    assert "submission_id" in body


@pytest.mark.django_db
def test_text_too_short_returns_422_text_too_short(settings):
    """CS-053 will surface TEXT_TOO_SHORT; CS-056 already maps it to HTTP 422."""

    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    client = APIClient()
    pdf = _tiny_pdf()

    with patch(
        "ingestion.application.upload_service._run_extractor",
        side_effect=NotAnalyzableError(
            reason=NotAnalyzableReason.TEXT_TOO_SHORT,
            message="extracted 120 chars < 500",
        ),
    ):
        resp = client.post(
            "/api/v1/submissions/",
            {
                "file": pdf,
                "disclaimer_accepted": "true",
                "disclaimer_method": DisclaimerAcceptanceMethod.CHECKBOX.value,
            },
            format="multipart",
        )

    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "TEXT_TOO_SHORT"


@pytest.mark.django_db
def test_successful_submission_remains_201(settings):
    """Sanity: 422 mapping must not fire when the submission succeeds."""

    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    client = APIClient()
    pdf = _tiny_pdf()
    fake_result = ExtractionResult(
        text="texto en español de prueba con suficiente longitud para pasar",
        token_count=12,
        language="es",
        page_count=1,
    )
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=fake_result,
    ):
        resp = client.post(
            "/api/v1/submissions/",
            {
                "file": pdf,
                "disclaimer_accepted": "true",
                "disclaimer_method": DisclaimerAcceptanceMethod.CHECKBOX.value,
            },
            format="multipart",
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["processing_status"] == ProcessingStatus.EXTRACTED.value
