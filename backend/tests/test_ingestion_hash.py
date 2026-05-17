"""CS-051: PRD §US-03 submission-hash composition rules."""

from __future__ import annotations

import hashlib

import pytest

from django.utils import timezone

from ingestion.application.upload_service import (
    FileUpload,
    UploadRequest,
    _compose_submission_hash,
    ingest_upload,
)
from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    ExtractionStrategy,
    SubmissionSource,
)


def _file(file_bytes: bytes, filename: str) -> FileUpload:
    return FileUpload(file_bytes=file_bytes, filename=filename, content_type="application/pdf")


def _expected_multi_hash(files: list[tuple[bytes, str]]) -> str:
    """Mirror the PRD §US-03 composition rule for verification."""

    per_file = sorted((filename, hashlib.sha256(b).hexdigest()) for b, filename in files)
    return hashlib.sha256("".join(h for _, h in per_file).encode("ascii")).hexdigest()


def test_single_file_hash_collapses_to_sha256_of_bytes():
    bytes_ = b"%PDF-1.5 single file"
    composed = _compose_submission_hash((_file(bytes_, "a.pdf"),))
    assert composed == hashlib.sha256(bytes_).hexdigest()


def test_multi_file_hash_is_deterministic_under_filename_ordering():
    """Same bytes + same filenames in two upload orders → same hash."""

    f1 = (b"alfa contents", "alfa.pdf")
    f2 = (b"beta contents", "beta.pdf")

    in_order = _compose_submission_hash((_file(*f1), _file(*f2)))
    swapped = _compose_submission_hash((_file(*f2), _file(*f1)))
    assert in_order == swapped


def test_multi_file_hash_changes_when_filename_changes():
    """PRD §US-03 — renaming a file changes the composed hash."""

    composed_a = _compose_submission_hash((_file(b"alfa contents", "alfa.pdf"), _file(b"beta contents", "beta.pdf")))
    composed_renamed = _compose_submission_hash(
        (_file(b"alfa contents", "renamed.pdf"), _file(b"beta contents", "beta.pdf"))
    )
    assert composed_a != composed_renamed


def test_multi_file_hash_matches_canonical_formula():
    """Match PRD §US-03 formula explicitly to lock the algorithm."""

    payload = [
        (b"alfa contents", "alfa.pdf"),
        (b"beta contents", "beta.pdf"),
        (b"charlie contents", "charlie.pdf"),
    ]
    composed = _compose_submission_hash(tuple(_file(b, fn) for b, fn in payload))
    assert composed == _expected_multi_hash(payload)


@pytest.mark.django_db
def test_idempotent_multi_file_resubmission_returns_existing(settings):
    """Resubmitting the same set of files returns the prior submission."""

    settings.OCR_MAX_BYTES = 10 * 1024 * 1024
    from unittest.mock import patch  # local import keeps the module light

    from ingestion.application.ocr.errors import ExtractionResult

    fake_result = ExtractionResult(
        text="texto en español con suficiente longitud para pasar el gate de idioma",
        token_count=10,
        language="es",
        page_count=1,
    )
    req = UploadRequest(
        files=(
            _file(b"%PDF-1.1 alfa\n", "alfa.pdf"),
            _file(b"%PDF-1.1 beta\n", "beta.pdf"),
        ),
        disclaimer_accepted_at=timezone.now(),
        disclaimer_method=DisclaimerAcceptanceMethod.CHECKBOX,
        source=SubmissionSource.WEB,
        force_strategy=ExtractionStrategy.PYPDF,
    )
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=fake_result,
    ):
        first = ingest_upload(req)
        second = ingest_upload(req)
    assert first.created is True
    assert second.created is False
    assert first.submission.id == second.submission.id
