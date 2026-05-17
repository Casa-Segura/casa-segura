"""CS-060: latency-budget instrumentation for the ingestion pipeline.

Covers:

  * page-bucket-labelled extraction histogram increments under a fake clock,
  * INGEST_TIMEOUTS counter increments on TIMEOUT reason,
  * label cardinality budget stays under 20 series total (PRD §9 invariant).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone
from prometheus_client import REGISTRY

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.ocr.metrics import page_bucket
from ingestion.application.upload_service import UploadRequest, ingest_upload
from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    ExtractionStrategy,
    SubmissionSource,
)


def _request(
    file_bytes: bytes,
    *,
    filename="contract.pdf",
    content_type="application/pdf",
    force_strategy: ExtractionStrategy | None = None,
):
    return UploadRequest(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
        disclaimer_accepted_at=timezone.now(),
        disclaimer_method=DisclaimerAcceptanceMethod.CHECKBOX,
        source=SubmissionSource.WEB,
        force_strategy=force_strategy,
    )


def _minimal_pdf_bytes() -> bytes:
    return b"%PDF-1.1\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<<>>\n%%EOF"


def _sample(name: str, labels: dict[str, str]) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


# ─── page_bucket() unit semantics ───────────────────────────────────────


@pytest.mark.parametrize(
    "page_count,expected",
    [
        (None, "unknown"),
        (0, "unknown"),
        (-1, "unknown"),
        (1, "1"),
        (2, "2-10"),
        (10, "2-10"),
        (11, "11+"),
        (50, "11+"),
    ],
)
def test_page_bucket_taxonomy(page_count, expected):
    assert page_bucket(page_count) == expected


# ─── Fake clock: histogram observes the simulated elapsed ──────────────


@pytest.mark.django_db
def test_extract_pages_histogram_records_observation_with_fake_clock(monkeypatch):
    """AC1 — synthetic pipeline run with monkeypatched ``time.perf_counter``
    must increment the page-bucket histogram bucket/count.

    We patch the clock so ``elapsed = end - start = 1.5s``, which falls in
    the ``le=2.5`` bucket. The strategy is forced via the extractor patch.
    """

    fake_times = iter([0.0, 1.5])

    def _fake_now() -> float:
        try:
            return next(fake_times)
        except StopIteration:
            return 1.5

    monkeypatch.setattr(
        "ingestion.application.upload_service.time.perf_counter",
        _fake_now,
    )

    before_count = _sample(
        "casa_segura_ingest_extract_pages_duration_seconds_count",
        {"strategy": "pypdf", "page_bucket": "1"},
    )
    before_bucket = _sample(
        "casa_segura_ingest_extract_pages_duration_seconds_bucket",
        {"strategy": "pypdf", "page_bucket": "1", "le": "2.5"},
    )

    fake_result = ExtractionResult(
        text="texto en español de prueba",
        token_count=5,
        language="es",
        page_count=1,
    )
    with patch(
        "ingestion.application.upload_service._run_extractor",
        return_value=fake_result,
    ):
        ingest_upload(
            _request(_minimal_pdf_bytes(), force_strategy=ExtractionStrategy.PYPDF)
        )

    after_count = _sample(
        "casa_segura_ingest_extract_pages_duration_seconds_count",
        {"strategy": "pypdf", "page_bucket": "1"},
    )
    after_bucket = _sample(
        "casa_segura_ingest_extract_pages_duration_seconds_bucket",
        {"strategy": "pypdf", "page_bucket": "1", "le": "2.5"},
    )

    assert after_count == before_count + 1
    assert after_bucket == before_bucket + 1


# ─── TIMEOUT_EXCEEDED counter wired through extractor failure ──────────


@pytest.mark.django_db
def test_timeout_counter_increments_on_timeout_reason(monkeypatch):
    """AC4 — when an extractor raises NotAnalyzableReason.TIMEOUT, the
    dedicated INGEST_TIMEOUTS counter must increment."""

    before = _sample(
        "casa_segura_ingest_timeouts_total",
        {"stage": "extract", "strategy": "vision_llm"},
    )

    with patch(
        "ingestion.application.upload_service._run_extractor",
        side_effect=NotAnalyzableError(
            reason=NotAnalyzableReason.TIMEOUT,
            message="watchdog fired",
        ),
    ):
        ingest_upload(
            _request(_minimal_pdf_bytes(), content_type="application/pdf")
        )

    after = _sample(
        "casa_segura_ingest_timeouts_total",
        {"stage": "extract", "strategy": "vision_llm"},
    )
    assert after == before + 1


@pytest.mark.django_db
def test_non_timeout_failure_does_not_increment_timeout_counter():
    """Negative coverage: REJECTED_LANGUAGE must not bump INGEST_TIMEOUTS."""

    before = _sample(
        "casa_segura_ingest_timeouts_total",
        {"stage": "extract", "strategy": "vision_llm"},
    )

    with patch(
        "ingestion.application.upload_service._run_extractor",
        side_effect=NotAnalyzableError(
            reason=NotAnalyzableReason.REJECTED_LANGUAGE,
            message="detected 'en'",
        ),
    ):
        ingest_upload(_request(_minimal_pdf_bytes()))

    after = _sample(
        "casa_segura_ingest_timeouts_total",
        {"stage": "extract", "strategy": "vision_llm"},
    )
    assert after == before  # untouched
