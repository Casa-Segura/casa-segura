"""Upload service + routing tests (CS-050, 051, 052, 056, 059).

We patch the real extractors so the suite stays hermetic: pypdf is hit
through router probing only, Pixtral and Tesseract are mocked entirely.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.upload_service import UploadRequest, ingest_upload
from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    OcrJobStatus,
    ProcessingStatus,
    SubmissionSource,
)


def _request(file_bytes: bytes, *, filename="contract.pdf", content_type="application/pdf"):
    return UploadRequest(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        disclaimer_accepted_at=timezone.now(),
        disclaimer_method=DisclaimerAcceptanceMethod.CHECKBOX,
        source=SubmissionSource.WEB,
    )


def _fake_result(text="texto de prueba en español", token_count=42, page_count=1):
    return ExtractionResult(
        text=text,
        token_count=token_count,
        language="es",
        page_count=page_count,
    )


def _minimal_pdf_bytes() -> bytes:
    """Tiny but structurally valid PDF that pypdf will refuse to extract
    enough text from (forcing the router to choose vision)."""

    return b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"


# ─── CS-059: size BVA ───────────────────────────────────────────────────


@pytest.mark.django_db
def test_size_zero_bytes_is_rejected_as_empty_file():
    with pytest.raises(NotAnalyzableError) as exc:
        ingest_upload(_request(b""))
    assert exc.value.reason == NotAnalyzableReason.EMPTY_FILE


@pytest.mark.django_db
def test_size_one_byte_passes_validation_then_falls_to_routing():
    # 1 byte clears the size cap (>0). It must reach extraction and be
    # rejected there — the orchestrator captures the NotAnalyzableError
    # and persists the failure on the submission rather than re-raising.
    with patch(
        "ingestion.application.upload_service._run_extractor",
        side_effect=NotAnalyzableError(
            reason=NotAnalyzableReason.UPSTREAM_LLM_ERROR,
            message="pixtral could not parse 1 byte",
        ),
    ):
        outcome = ingest_upload(_request(b"x"))
    assert outcome.created is True
    assert outcome.submission.processing_status == ProcessingStatus.FAILED_EXTRACTION.value
    assert outcome.submission.error_code == NotAnalyzableReason.UPSTREAM_LLM_ERROR.value


@pytest.mark.django_db
def test_size_exactly_max_is_accepted(settings):
    settings.OCR_MAX_BYTES = 1024
    # Patch the strategy attempt so it succeeds.
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(),
    ):
        outcome = ingest_upload(_request(b"x" * 1024))
    assert outcome.created is True
    assert outcome.submission.processing_status == ProcessingStatus.EXTRACTED.value


@pytest.mark.django_db
def test_size_one_over_max_is_rejected(settings):
    settings.OCR_MAX_BYTES = 1024
    with pytest.raises(NotAnalyzableError) as exc:
        ingest_upload(_request(b"x" * 1025))
    assert exc.value.reason == NotAnalyzableReason.SIZE_EXCEEDED


# ─── CS-051: idempotency by SHA-256 ─────────────────────────────────────


@pytest.mark.django_db
def test_idempotent_resubmission_returns_existing(settings):
    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(),
    ):
        first = ingest_upload(_request(_minimal_pdf_bytes()))
        second = ingest_upload(_request(_minimal_pdf_bytes()))
    assert first.created is True
    assert second.created is False
    assert first.submission.id == second.submission.id


@pytest.mark.django_db
def test_different_bytes_yield_different_submission_ids():
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(),
    ):
        first = ingest_upload(_request(_minimal_pdf_bytes()))
        second = ingest_upload(_request(_minimal_pdf_bytes() + b"\n%suffix"))
    assert first.submission.id != second.submission.id


# ─── CS-056: not_analyzable envelope on failures ────────────────────────


@pytest.mark.django_db
def test_failed_extractor_marks_submission_failed_and_records_error_code():
    with patch(
        "ingestion.application.upload_service._run_extractor",
        side_effect=NotAnalyzableError(
            reason=NotAnalyzableReason.REJECTED_LANGUAGE,
            message="detected 'en'",
        ),
    ):
        outcome = ingest_upload(_request(_minimal_pdf_bytes()))

    assert outcome.created is True
    assert outcome.submission.processing_status == ProcessingStatus.REJECTED_LANGUAGE.value
    assert outcome.submission.error_code == NotAnalyzableReason.REJECTED_LANGUAGE.value


# ─── CS-059: page-count cap BVA ─────────────────────────────────────────


@pytest.mark.django_db
@pytest.mark.parametrize(
    "page_count,expected_status",
    [
        (1, ProcessingStatus.EXTRACTED.value),
        (49, ProcessingStatus.EXTRACTED.value),
        (50, ProcessingStatus.EXTRACTED.value),
        (51, ProcessingStatus.REJECTED_SIZE.value),
    ],
)
def test_page_count_bva(page_count, expected_status, settings):
    settings.OCR_MAX_PAGES = 50
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(page_count=page_count),
    ):
        outcome = ingest_upload(_request(_minimal_pdf_bytes()))
    assert outcome.submission.processing_status == expected_status


# ─── CS-052: routing + 1 OcrJob per attempt ────────────────────────────


@pytest.mark.django_db
def test_extraction_creates_one_ocr_job_on_success():
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(),
    ):
        outcome = ingest_upload(_request(_minimal_pdf_bytes()))
    jobs = outcome.submission.ocr_jobs.all()
    assert len(jobs) == 1
    assert jobs[0].status == OcrJobStatus.SUCCESS.value
    assert outcome.submission.extraction_strategy_successful is not None
