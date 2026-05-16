"""Upload + OCR orchestration (CS-050 + CS-051 + CS-052 + CS-057 + CS-059 + CS-060).

Receives a freshly uploaded file, validates caps, computes the SHA-256
hash for idempotency, routes through the extractor selected by
`ocr.router.detect_kind`, persists only metadata (token count + language
+ status — never the extracted text), and emits per-stage Prometheus
metrics.

Public surface:

  * `ingest_upload(...)` → returns the persisted `ContractSubmission`.

The function is intentionally synchronous: in Phase 1 the request is
served end-to-end inside the worker process. Async pipelining via Celery
will be added in Phase 2 (see CS-060 follow-ups).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime

import structlog

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.ocr.extractors.pixtral import extract_via_pixtral
from ingestion.application.ocr.extractors.pypdf_extractor import extract_text_pdf
from ingestion.application.ocr.extractors.tesseract import extract_via_tesseract
from ingestion.application.ocr.metrics import INGEST_OUTCOMES, INGEST_STAGE_DURATION
from ingestion.application.ocr.router import detect_kind
from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    ExtractionStrategy,
    FileFormat,
    OcrJobStatus,
    ProcessingStatus,
    SubmissionSource,
)
from ingestion.infrastructure.django.models import ContractSubmission, OcrJob

logger = structlog.get_logger(__name__)


_ALLOWED_FORMATS = {f.value for f in FileFormat}
_SUCCESS_STATUSES = {OcrJobStatus.SUCCESS}


@dataclass(frozen=True)
class UploadRequest:
    file_bytes: bytes
    filename: str
    content_type: str
    disclaimer_accepted_at: datetime
    disclaimer_method: DisclaimerAcceptanceMethod = DisclaimerAcceptanceMethod.CHECKBOX
    source: SubmissionSource = SubmissionSource.WEB


@dataclass(frozen=True)
class IngestOutcome:
    submission: ContractSubmission
    created: bool


def ingest_upload(req: UploadRequest) -> IngestOutcome:
    """Validate + ingest a single uploaded file. Idempotent by SHA-256."""

    _validate_size(req.file_bytes)
    _validate_format(req.filename, req.content_type)

    submission_hash = _hash_bytes(req.file_bytes)

    existing = ContractSubmission.objects.filter(submission_hash=submission_hash).first()
    if existing is not None:
        logger.info(
            "ingest.idempotent_hit",
            submission_id=str(existing.id),
            status=existing.processing_status,
        )
        return IngestOutcome(submission=existing, created=False)

    routing = _timed(
        "route",
        "unknown",
        detect_kind,
        content_type=req.content_type,
        file_bytes=req.file_bytes,
        filename=req.filename,
    )

    submission = _create_initial_submission(
        req=req,
        submission_hash=submission_hash,
        routing_strategy=routing.strategy,
        file_format=routing.file_format,
    )

    try:
        result = _attempt_extraction(submission, req=req, primary=routing.strategy)
        _enforce_page_cap(result)
    except NotAnalyzableError as exc:
        _mark_failed(submission, exc)
        INGEST_OUTCOMES.labels(outcome="rejected", error_code=exc.reason.value).inc()
        return IngestOutcome(submission=submission, created=True)

    _persist_success(submission, result=result)
    INGEST_OUTCOMES.labels(outcome="success", error_code="").inc()
    return IngestOutcome(submission=submission, created=True)


def _enforce_page_cap(result: ExtractionResult) -> None:
    """Reject submissions exceeding `OCR_MAX_PAGES` once we know the count."""

    if result.page_count is not None and result.page_count > settings.OCR_MAX_PAGES:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.PAGE_COUNT_EXCEEDED,
            message=f"page_count {result.page_count} > {settings.OCR_MAX_PAGES}",
        )


# ─── helpers ────────────────────────────────────────────────────────────


def _validate_size(file_bytes: bytes) -> None:
    if not file_bytes:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.EMPTY_FILE,
            message="received 0 bytes",
        )
    if len(file_bytes) > settings.OCR_MAX_BYTES:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.SIZE_EXCEEDED,
            message=f"size {len(file_bytes)} > {settings.OCR_MAX_BYTES}",
        )


def _validate_format(filename: str, content_type: str) -> None:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    ct = (content_type or "").lower()
    # Allow if either the extension or the MIME maps to a supported format.
    if ext in _ALLOWED_FORMATS:
        return
    mime_to_ext = {
        "application/pdf": "pdf",
        "image/jpeg": "jpeg",
        "image/jpg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/heic": "heic",
    }
    if ct in mime_to_ext:
        return
    raise NotAnalyzableError(
        reason=NotAnalyzableReason.UNSUPPORTED_FORMAT,
        message=f"format/mime not supported: {ext!r}/{ct!r}",
    )


def _hash_bytes(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


@transaction.atomic
def _create_initial_submission(
    *,
    req: UploadRequest,
    submission_hash: str,
    routing_strategy: ExtractionStrategy,
    file_format: FileFormat,
) -> ContractSubmission:
    return ContractSubmission.objects.create(
        submission_hash=submission_hash,
        file_format=file_format.value,
        file_size_bytes=len(req.file_bytes),
        file_count=1,
        source=req.source.value,
        disclaimer_accepted_at=req.disclaimer_accepted_at or timezone.now(),
        disclaimer_method=req.disclaimer_method.value,
        processing_status=ProcessingStatus.EXTRACTING.value,
        extraction_strategy_attempted=routing_strategy.value,
    )


def _attempt_extraction(
    submission: ContractSubmission,
    *,
    req: UploadRequest,
    primary: ExtractionStrategy,
) -> ExtractionResult:
    """Try the primary strategy; fall back to Tesseract for image-likely
    failures when the LLM path errors. PDFs that fail Pixtral are NOT
    fed to Tesseract (rasterisation is out of scope for Phase 1)."""

    order: list[ExtractionStrategy] = [primary]
    if primary == ExtractionStrategy.VISION_LLM and _is_image_mime(req.content_type):
        order.append(ExtractionStrategy.TESSERACT)

    last_error: NotAnalyzableError | None = None
    for strategy in order:
        job = OcrJob.objects.create(
            submission=submission,
            strategy=strategy.value,
            attempt_number=submission.ocr_jobs.count() + 1,
        )
        try:
            result = _timed(
                "extract",
                strategy.value,
                _run_extractor,
                strategy=strategy,
                req=req,
            )
        except NotAnalyzableError as exc:
            job.status = _job_status_for(exc.reason)
            job.error = str(exc)
            job.error_code = exc.reason.value
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error", "error_code", "completed_at"])
            last_error = exc
            continue
        else:
            job.status = OcrJobStatus.SUCCESS.value
            job.completed_at = timezone.now()
            job.tokens_consumed = result.tokens_consumed
            job.cost_estimate_cents = result.cost_estimate_cents
            job.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "tokens_consumed",
                    "cost_estimate_cents",
                ]
            )
            submission.extraction_strategy_successful = strategy.value
            submission.save(update_fields=["extraction_strategy_successful"])
            return result

    if last_error is None:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.OCR_UNAVAILABLE,
            message="extraction loop exited without any attempt",
        )
    raise last_error


def _run_extractor(*, strategy: ExtractionStrategy, req: UploadRequest) -> ExtractionResult:
    if strategy == ExtractionStrategy.PYPDF:
        return extract_text_pdf(req.file_bytes)
    if strategy == ExtractionStrategy.VISION_LLM:
        return extract_via_pixtral(
            file_bytes=req.file_bytes,
            content_type=req.content_type,
            filename=req.filename,
        )
    if strategy == ExtractionStrategy.TESSERACT:
        return extract_via_tesseract(file_bytes=req.file_bytes, content_type=req.content_type)
    raise NotAnalyzableError(
        reason=NotAnalyzableReason.OCR_UNAVAILABLE,
        message=f"no extractor for strategy {strategy}",
    )


def _is_image_mime(content_type: str) -> bool:
    return (content_type or "").lower().startswith("image/")


def _job_status_for(reason: NotAnalyzableReason) -> str:
    if reason == NotAnalyzableReason.TIMEOUT:
        return OcrJobStatus.TIMEOUT.value
    return OcrJobStatus.FAILED.value


def _persist_success(submission: ContractSubmission, *, result: ExtractionResult) -> None:
    """Persist ONLY metadata. The text is intentionally not stored
    anywhere (CS-057 invariant: no `extracted_text` column exists)."""

    submission.processing_status = ProcessingStatus.EXTRACTED.value
    submission.extracted_text_token_count = result.token_count
    submission.extracted_text_language = result.language
    submission.page_count = result.page_count
    submission.save(
        update_fields=[
            "processing_status",
            "extracted_text_token_count",
            "extracted_text_language",
            "page_count",
        ]
    )


def _mark_failed(submission: ContractSubmission, exc: NotAnalyzableError) -> None:
    status_map = {
        NotAnalyzableReason.REJECTED_LANGUAGE: ProcessingStatus.REJECTED_LANGUAGE,
        NotAnalyzableReason.SIZE_EXCEEDED: ProcessingStatus.REJECTED_SIZE,
        NotAnalyzableReason.PAGE_COUNT_EXCEEDED: ProcessingStatus.REJECTED_SIZE,
        NotAnalyzableReason.UNSUPPORTED_FORMAT: ProcessingStatus.REJECTED_TYPE,
    }
    submission.processing_status = status_map.get(exc.reason, ProcessingStatus.FAILED_EXTRACTION).value
    submission.error_code = exc.reason.value
    submission.error_reason = exc.message[:1000]
    submission.save(update_fields=["processing_status", "error_code", "error_reason"])


def _timed(stage: str, strategy: str, fn, /, *args, **kwargs):
    """Execute `fn`, recording its wall-clock latency under the given stage label."""

    start = time.perf_counter()
    try:
        return fn(*args, **kwargs)
    finally:
        elapsed = time.perf_counter() - start
        INGEST_STAGE_DURATION.labels(stage=stage, strategy=strategy).observe(elapsed)
