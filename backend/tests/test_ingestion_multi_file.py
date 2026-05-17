"""CS-050: multi-file upload — 1..50 files, image dimensions, batch caps."""

from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.upload_service import (
    FileUpload,
    UploadRequest,
    ingest_upload,
)
from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    ExtractionStrategy,
    ProcessingStatus,
    SubmissionSource,
)


def _png_bytes(width: int, height: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "white").save(buf, format="PNG")
    return buf.getvalue()


def _pdf_bytes(suffix: bytes = b"") -> bytes:
    return (
        b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"
        + suffix
    )


def _file(file_bytes: bytes, filename: str, content_type: str) -> FileUpload:
    return FileUpload(file_bytes=file_bytes, filename=filename, content_type=content_type)


def _request(files: tuple[FileUpload, ...]) -> UploadRequest:
    return UploadRequest(
        files=files,
        disclaimer_accepted_at=timezone.now(),
        disclaimer_method=DisclaimerAcceptanceMethod.CHECKBOX,
        source=SubmissionSource.WEB,
        force_strategy=ExtractionStrategy.PYPDF,
    )


def _fake_result(text="texto en español de prueba con suficiente longitud", page_count=1):
    return ExtractionResult(text=text, token_count=8, language="es", page_count=page_count)


# ─── File-count caps (1..50) ───────────────────────────────────────────


@pytest.mark.django_db
def test_zero_files_rejected_as_empty(settings):
    with pytest.raises(NotAnalyzableError) as exc:
        ingest_upload(_request(files=()))
    assert exc.value.reason == NotAnalyzableReason.EMPTY_FILE


@pytest.mark.django_db
def test_50_files_accepted_at_cap(settings):
    """50 files (PRD §US-01 cap) must pass batch validation."""

    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    files = tuple(
        _file(_pdf_bytes(f"\n%{i}".encode()), f"contract_{i}.pdf", "application/pdf")
        for i in range(50)
    )
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(page_count=1),
    ):
        outcome = ingest_upload(_request(files=files))
    assert outcome.submission.file_count == 50
    assert outcome.submission.processing_status == ProcessingStatus.EXTRACTED.value


@pytest.mark.django_db
def test_51_files_rejected_with_too_many_files(settings):
    """51 files crosses the PRD cap → TOO_MANY_FILES."""

    files = tuple(
        _file(_pdf_bytes(f"\n%{i}".encode()), f"contract_{i}.pdf", "application/pdf")
        for i in range(51)
    )
    with pytest.raises(NotAnalyzableError) as exc:
        ingest_upload(_request(files=files))
    assert exc.value.reason == NotAnalyzableReason.TOO_MANY_FILES


# ─── Image dimension validator ─────────────────────────────────────────


@pytest.mark.parametrize(
    "width,height",
    [
        (599, 800),     # 1px under min width
        (600, 799),     # 1px under min height
        (8001, 10000),  # 1px over max width
        (600, 10001),   # 1px over max height
    ],
)
@pytest.mark.django_db
def test_image_dimensions_outside_bounds_rejected(width, height):
    with pytest.raises(NotAnalyzableError) as exc:
        ingest_upload(
            _request(files=(_file(_png_bytes(width, height), "shot.png", "image/png"),))
        )
    assert exc.value.reason == NotAnalyzableReason.IMAGE_DIMENSIONS_INVALID


@pytest.mark.parametrize(
    "width,height",
    [(600, 800), (8000, 10000)],
)
@pytest.mark.django_db
def test_image_dimensions_at_bounds_accepted(width, height):
    """Min (600,800) and max (8000,10000) are inclusive per PRD."""

    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(page_count=1),
    ):
        outcome = ingest_upload(
            UploadRequest(
                files=(_file(_png_bytes(width, height), "shot.png", "image/png"),),
                disclaimer_accepted_at=timezone.now(),
                disclaimer_method=DisclaimerAcceptanceMethod.CHECKBOX,
                source=SubmissionSource.WEB,
                force_strategy=ExtractionStrategy.VISION_LLM,
            )
        )
    assert outcome.submission.processing_status == ProcessingStatus.EXTRACTED.value


# ─── Total size caps (≤100 MB combined) + per-file (FILE_TOO_LARGE) ────


@pytest.mark.django_db
def test_combined_size_over_100mb_rejected(settings):
    """100 MB + 1 byte across the batch → TOTAL_SIZE_TOO_LARGE."""

    settings.OCR_MAX_BYTES = 60 * 1024 * 1024
    # Two files at 50 MB each + 1 byte → 100 MB + 1 byte combined.
    big = b"x" * (50 * 1024 * 1024)
    files = (
        _file(big, "a.pdf", "application/pdf"),
        _file(big + b"x", "b.pdf", "application/pdf"),
    )
    with pytest.raises(NotAnalyzableError) as exc:
        ingest_upload(_request(files=files))
    assert exc.value.reason == NotAnalyzableReason.TOTAL_SIZE_TOO_LARGE


@pytest.mark.django_db
def test_single_file_over_max_bytes_rejected(settings):
    """Single file >OCR_MAX_BYTES → FILE_TOO_LARGE (CS-050 envelope)."""

    settings.OCR_MAX_BYTES = 1024
    with pytest.raises(NotAnalyzableError) as exc:
        ingest_upload(_request(files=(_file(b"x" * 1025, "a.pdf", "application/pdf"),)))
    assert exc.value.reason == NotAnalyzableReason.FILE_TOO_LARGE


# ─── Combined pages cap ≤80 ────────────────────────────────────────────


@pytest.mark.django_db
def test_combined_pages_over_80_rejected(settings):
    """Multi-file submission whose pages sum to 81 → PAGE_COUNT_EXCEEDED (TOO_MANY_PAGES)."""

    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    settings.OCR_MAX_PAGES = 50
    files = (
        _file(_pdf_bytes(b"\n%a"), "a.pdf", "application/pdf"),
        _file(_pdf_bytes(b"\n%b"), "b.pdf", "application/pdf"),
    )
    with patch(
        "ingestion.application.upload_service._run_extractor",
        # Each file yields 41 pages → 82 combined. (per-file ≤50 OK).
        return_value=_fake_result(page_count=41),
    ):
        outcome = ingest_upload(_request(files=files))
    assert outcome.submission.processing_status == ProcessingStatus.REJECTED_SIZE.value
    assert outcome.submission.error_code == NotAnalyzableReason.PAGE_COUNT_EXCEEDED.value


# ─── Multi-file: API multipart payload ─────────────────────────────────


@pytest.mark.django_db
def test_api_accepts_files_array_payload(settings):
    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    client = APIClient()

    pdf_one = SimpleUploadedFile("a.pdf", _pdf_bytes(b"\n%a"), content_type="application/pdf")
    pdf_two = SimpleUploadedFile("b.pdf", _pdf_bytes(b"\n%b"), content_type="application/pdf")

    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(page_count=1),
    ):
        resp = client.post(
            "/api/v1/submissions/",
            {
                "files": [pdf_one, pdf_two],
                "disclaimer_accepted": "true",
                "disclaimer_method": DisclaimerAcceptanceMethod.CHECKBOX.value,
            },
            format="multipart",
            HTTP_X_FORCE_STRATEGY="pypdf",
        )

    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["file_count"] == 2


@pytest.mark.django_db
def test_api_legacy_single_file_field_still_accepted(settings):
    """Backwards compat — pre-CS-050 callers send `file=…` (singular)."""

    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    client = APIClient()
    pdf = SimpleUploadedFile("c.pdf", _pdf_bytes(), content_type="application/pdf")

    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=_fake_result(page_count=1),
    ):
        resp = client.post(
            "/api/v1/submissions/",
            {
                "file": pdf,
                "disclaimer_accepted": "true",
                "disclaimer_method": DisclaimerAcceptanceMethod.CHECKBOX.value,
            },
            format="multipart",
            HTTP_X_FORCE_STRATEGY="pypdf",
        )
    assert resp.status_code == 201, resp.content
    assert resp.json()["file_count"] == 1
