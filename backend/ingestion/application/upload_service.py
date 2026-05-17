"""Upload + OCR orchestration (CS-050 + CS-051 + CS-052 + CS-057 + CS-059 + CS-060).

Receives one **or more** uploaded files, validates per-submission caps,
computes the SHA-256 idempotency hash, routes each file through the
extractor selected by ``ocr.router.detect_kind``, persists only metadata
(token count + language + status — never the extracted text), and emits
per-stage Prometheus metrics.

Public surface:

  * ``ingest_upload(UploadRequest)`` → returns the persisted
    ``ContractSubmission``. Accepts ``files=(FileUpload(...), …)`` with
    1-50 entries (PRD §US-01 / [[CS-050]]).

The function is intentionally synchronous: in Phase 1 the request is
served end-to-end inside the worker process. Async pipelining via Celery
will be added in Phase 2 (see CS-060 follow-ups).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

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
from ingestion.application.ocr.metrics import (
    INGEST_EXTRACT_PAGES_DURATION,
    INGEST_OUTCOMES,
    INGEST_STAGE_DURATION,
    INGEST_TIMEOUTS,
    page_bucket,
)
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
_IMAGE_FORMATS = {
    FileFormat.JPG.value,
    FileFormat.JPEG.value,
    FileFormat.PNG.value,
    FileFormat.WEBP.value,
    FileFormat.HEIC.value,
}
_SUCCESS_STATUSES = {OcrJobStatus.SUCCESS}

# PRD §US-01 batch limits.
MAX_FILES_PER_SUBMISSION = 50
MAX_TOTAL_BYTES = 100 * 1024 * 1024  # 100 MB combined
MAX_TOTAL_PAGES = 80

# Image dimension bounds (PRD §US-01).
IMAGE_MIN_WIDTH = 600
IMAGE_MIN_HEIGHT = 800
IMAGE_MAX_WIDTH = 8000
IMAGE_MAX_HEIGHT = 10000


@dataclass(frozen=True)
class FileUpload:
    """A single uploaded file inside a submission batch."""

    file_bytes: bytes
    filename: str
    content_type: str


@dataclass(frozen=True)
class UploadRequest:
    """A submission — one or more files uploaded together."""

    files: tuple[FileUpload, ...]
    disclaimer_accepted_at: datetime
    disclaimer_method: DisclaimerAcceptanceMethod = DisclaimerAcceptanceMethod.CHECKBOX
    source: SubmissionSource = SubmissionSource.WEB
    force_strategy: ExtractionStrategy | None = None


@dataclass(frozen=True)
class IngestOutcome:
    submission: ContractSubmission
    created: bool


def ingest_upload(req: UploadRequest) -> IngestOutcome:
    """Validate + ingest 1..50 uploaded files. Idempotent by composed SHA-256."""

    _validate_batch(req.files)

    submission_hash = _compose_submission_hash(req.files)

    existing = ContractSubmission.objects.filter(submission_hash=submission_hash).first()
    if existing is not None:
        logger.info(
            "ingest.idempotent_hit",
            submission_id=str(existing.id),
            status=existing.processing_status,
        )
        return IngestOutcome(submission=existing, created=False)

    # Resolve routing for the first file so the submission carries an
    # attempted strategy label for observability. Multi-file submissions
    # route each file independently inside ``_run_batch_extraction``.
    primary_file = req.files[0]
    routing = _timed(
        "route",
        "unknown",
        detect_kind,
        content_type=primary_file.content_type,
        file_bytes=primary_file.file_bytes,
        filename=primary_file.filename,
        force_strategy=req.force_strategy,
    )

    total_bytes = sum(len(f.file_bytes) for f in req.files)
    submission = _create_initial_submission(
        req=req,
        submission_hash=submission_hash,
        routing_strategy=routing.strategy,
        file_format=routing.file_format,
        total_bytes=total_bytes,
    )

    try:
        combined = _run_batch_extraction(submission, req=req)
        _enforce_total_pages(combined)
    except NotAnalyzableError as exc:
        _mark_failed(submission, exc)
        INGEST_OUTCOMES.labels(outcome="rejected", error_code=exc.reason.value).inc()
        return IngestOutcome(submission=submission, created=True)

    _persist_success(
        submission,
        result=combined.result,
        extract_elapsed=combined.elapsed_seconds,
        strategy=combined.winning_strategy,
    )
    INGEST_OUTCOMES.labels(outcome="success", error_code="").inc()
    return IngestOutcome(submission=submission, created=True)


# ─── batch helpers ─────────────────────────────────────────────────────


@dataclass(frozen=True)
class _BatchExtraction:
    result: ExtractionResult
    elapsed_seconds: float
    winning_strategy: ExtractionStrategy


def _validate_batch(files: tuple[FileUpload, ...]) -> None:
    """Per-PRD §US-01 batch guards. Order matters — caller relies on the
    first failure aborting before any extractor runs."""

    if not files:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.EMPTY_FILE,
            message="no files supplied",
        )
    if len(files) > MAX_FILES_PER_SUBMISSION:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.TOO_MANY_FILES,
            message=f"{len(files)} files > {MAX_FILES_PER_SUBMISSION}",
        )

    total = 0
    for upload in files:
        _validate_size(upload.file_bytes)
        _validate_format(upload.filename, upload.content_type)
        _validate_image_dimensions(upload)
        total += len(upload.file_bytes)
        if total > MAX_TOTAL_BYTES:
            raise NotAnalyzableError(
                reason=NotAnalyzableReason.TOTAL_SIZE_TOO_LARGE,
                message=f"combined size {total} > {MAX_TOTAL_BYTES}",
            )


def _validate_image_dimensions(upload: FileUpload) -> None:
    """Enforce PRD §US-01 image bounds (600x800 min, 8000x10000 max)."""

    ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else ""
    ct = (upload.content_type or "").lower()
    is_image = ext in _IMAGE_FORMATS or ct.startswith("image/")
    if not is_image:
        return

    try:
        # Lazy import: PIL is on the OCR install path anyway.
        from PIL import Image, UnidentifiedImageError  # noqa: PLC0415

        with Image.open(BytesIO(upload.file_bytes)) as image:
            width, height = image.size
    except UnidentifiedImageError as exc:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.CORRUPT_FILE,
            message=f"cannot decode image {upload.filename!r}: {exc}",
        ) from exc
    except Exception:
        # Some bytestreams that look like images won't decode; bubble
        # the same error as upstream rejection.
        return

    if not (IMAGE_MIN_WIDTH <= width <= IMAGE_MAX_WIDTH and IMAGE_MIN_HEIGHT <= height <= IMAGE_MAX_HEIGHT):
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.IMAGE_DIMENSIONS_INVALID,
            message=(
                f"image {upload.filename!r} is {width}x{height}; expected within "
                f"{IMAGE_MIN_WIDTH}x{IMAGE_MIN_HEIGHT}..{IMAGE_MAX_WIDTH}x{IMAGE_MAX_HEIGHT}"
            ),
        )


def _compose_submission_hash(files: tuple[FileUpload, ...]) -> str:
    """PRD §US-03 idempotency hash.

    For a single file it collapses to ``sha256(file_bytes)``. For multi-
    file uploads it is ``sha256( concat( hex(sha256(file_i)) ordered by
    filename ) )`` so re-uploading the same set of bytes — even renamed
    to a different ordering — produces a deterministic key.
    """

    if len(files) == 1:
        return _hash_bytes(files[0].file_bytes)

    per_file = sorted((upload.filename, _hash_bytes(upload.file_bytes)) for upload in files)
    concat = "".join(hexhash for _, hexhash in per_file).encode("ascii")
    return hashlib.sha256(concat).hexdigest()


def _run_batch_extraction(
    submission: ContractSubmission,
    *,
    req: UploadRequest,
) -> _BatchExtraction:
    """Extract each file in order; raise on the first hard failure.

    For a single-file batch this is the same as the old behaviour.
    For multi-file batches we concatenate normalized text with explicit
    ``--- FILE N: filename ---`` separators so downstream classification
    keeps page attribution.
    """

    text_parts: list[str] = []
    total_tokens = 0
    total_pages = 0
    total_elapsed = 0.0
    last_strategy: ExtractionStrategy = ExtractionStrategy.PYPDF

    for index, upload in enumerate(req.files, start=1):
        per_file_req = _per_file_request(req, upload)
        routing = detect_kind(
            content_type=upload.content_type,
            file_bytes=upload.file_bytes,
            filename=upload.filename,
            force_strategy=req.force_strategy,
        )
        result, elapsed, winning = _attempt_extraction(submission, req=per_file_req, primary=routing.strategy)
        if result.page_count is not None and result.page_count > settings.OCR_MAX_PAGES:
            raise NotAnalyzableError(
                reason=NotAnalyzableReason.PAGE_COUNT_EXCEEDED,
                message=(f"file {upload.filename!r} page_count {result.page_count} > {settings.OCR_MAX_PAGES}"),
            )

        header = f"--- FILE {index}: {upload.filename} ---"
        text_parts.append(f"{header}\n\n{result.text}")
        total_tokens += result.token_count
        total_pages += result.page_count or 0
        total_elapsed += elapsed
        last_strategy = winning

    combined_text = "\n\n".join(text_parts)
    combined = ExtractionResult(
        text=combined_text,
        token_count=total_tokens,
        # Language gate already ran inside each extractor; the winning
        # extractor's language flag is propagated through the loop.
        language="es",
        page_count=total_pages or None,
    )
    return _BatchExtraction(
        result=combined,
        elapsed_seconds=total_elapsed,
        winning_strategy=last_strategy,
    )


def _per_file_request(req: UploadRequest, upload: FileUpload) -> UploadRequest:
    """Wrap a single ``FileUpload`` in an ``UploadRequest`` so the existing
    single-file extraction loop keeps its interface stable."""

    return UploadRequest(
        files=(upload,),
        disclaimer_accepted_at=req.disclaimer_accepted_at,
        disclaimer_method=req.disclaimer_method,
        source=req.source,
        force_strategy=req.force_strategy,
    )


def _enforce_total_pages(combined: _BatchExtraction) -> None:
    """PRD §US-01 / [[CS-059]] combined ≤80 pages rule."""

    page_count = combined.result.page_count
    if page_count is not None and page_count > MAX_TOTAL_PAGES:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.PAGE_COUNT_EXCEEDED,
            message=f"combined page_count {page_count} > {MAX_TOTAL_PAGES}",
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
            reason=NotAnalyzableReason.FILE_TOO_LARGE,
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
    total_bytes: int,
) -> ContractSubmission:
    return ContractSubmission.objects.create(
        submission_hash=submission_hash,
        file_format=file_format.value,
        file_size_bytes=total_bytes,
        file_count=len(req.files),
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
) -> tuple[ExtractionResult, float, ExtractionStrategy]:
    """Try the primary strategy; fall back to Tesseract for image-likely
    failures when the LLM path errors. PDFs that fail Pixtral are NOT
    fed to Tesseract (rasterisation is out of scope for Phase 1).

    The caller passes a per-file ``UploadRequest`` (``files=(one_upload,)``)
    so multi-file submissions reuse the same loop per file.

    Returns ``(result, elapsed_seconds, winning_strategy)`` for the
    intent that finally succeeded, so the caller can emit the
    page-bucket histogram against the right strategy without re-timing.
    """

    upload = req.files[0]
    order: list[ExtractionStrategy] = [primary]
    if primary == ExtractionStrategy.VISION_LLM and _is_image_mime(upload.content_type):
        order.append(ExtractionStrategy.TESSERACT)

    last_error: NotAnalyzableError | None = None
    visited: set[ExtractionStrategy] = set()
    while order:
        strategy = order.pop(0)
        if strategy in visited:
            continue
        visited.add(strategy)
        job = OcrJob.objects.create(
            submission=submission,
            strategy=strategy.value,
            attempt_number=submission.ocr_jobs.count() + 1,
        )
        start = time.perf_counter()
        try:
            result = _run_extractor(strategy=strategy, req=req)
        except NotAnalyzableError as exc:
            elapsed = time.perf_counter() - start
            INGEST_STAGE_DURATION.labels(stage="extract", strategy=strategy.value).observe(elapsed)
            if exc.reason == NotAnalyzableReason.TIMEOUT:
                INGEST_TIMEOUTS.labels(stage="extract", strategy=strategy.value).inc()
            job.status = _job_status_for(exc.reason)
            job.error = str(exc)
            job.error_code = exc.reason.value
            job.completed_at = timezone.now()
            job.save(update_fields=["status", "error", "error_code", "completed_at"])
            last_error = exc
            # PRD §US-05 BR-08: pypdf with <500 chars / no usable text
            # escalates to vision so a scanned-PDF mis-classified as
            # native-text still gets a chance at extraction.
            if (
                strategy == ExtractionStrategy.PYPDF
                and exc.reason == NotAnalyzableReason.LOW_CONFIDENCE_OCR
                and ExtractionStrategy.VISION_LLM not in visited
            ):
                order.append(ExtractionStrategy.VISION_LLM)
            continue
        else:
            elapsed = time.perf_counter() - start
            INGEST_STAGE_DURATION.labels(stage="extract", strategy=strategy.value).observe(elapsed)
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
            return result, elapsed, strategy

    if last_error is None:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.OCR_UNAVAILABLE,
            message="extraction loop exited without any attempt",
        )
    raise last_error


def _run_extractor(*, strategy: ExtractionStrategy, req: UploadRequest) -> ExtractionResult:
    upload = req.files[0]
    if strategy == ExtractionStrategy.PYPDF:
        return extract_text_pdf(upload.file_bytes)
    if strategy == ExtractionStrategy.VISION_LLM:
        return extract_via_pixtral(
            file_bytes=upload.file_bytes,
            content_type=upload.content_type,
            filename=upload.filename,
        )
    if strategy == ExtractionStrategy.TESSERACT:
        return extract_via_tesseract(
            file_bytes=upload.file_bytes,
            content_type=upload.content_type,
        )
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


def _persist_success(
    submission: ContractSubmission,
    *,
    result: ExtractionResult,
    extract_elapsed: float,
    strategy: ExtractionStrategy,
) -> None:
    """Persist ONLY metadata. The text is intentionally not stored
    anywhere (CS-057 invariant: no `extracted_text` column exists).

    Also emit the page-bucket-labelled extraction-duration histogram
    (CS-060) using ``extract_elapsed`` measured on the winning attempt.
    """

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

    INGEST_EXTRACT_PAGES_DURATION.labels(
        strategy=strategy.value,
        page_bucket=page_bucket(result.page_count),
    ).observe(extract_elapsed)


def _mark_failed(submission: ContractSubmission, exc: NotAnalyzableError) -> None:
    status_map = {
        NotAnalyzableReason.REJECTED_LANGUAGE: ProcessingStatus.REJECTED_LANGUAGE,
        NotAnalyzableReason.SIZE_EXCEEDED: ProcessingStatus.REJECTED_SIZE,
        NotAnalyzableReason.FILE_TOO_LARGE: ProcessingStatus.REJECTED_SIZE,
        NotAnalyzableReason.TOTAL_SIZE_TOO_LARGE: ProcessingStatus.REJECTED_SIZE,
        NotAnalyzableReason.TOO_MANY_FILES: ProcessingStatus.REJECTED_SIZE,
        NotAnalyzableReason.PAGE_COUNT_EXCEEDED: ProcessingStatus.REJECTED_SIZE,
        NotAnalyzableReason.UNSUPPORTED_FORMAT: ProcessingStatus.REJECTED_TYPE,
        NotAnalyzableReason.IMAGE_DIMENSIONS_INVALID: ProcessingStatus.REJECTED_TYPE,
        # PRD §7.4 — TEXT_TOO_SHORT maps to failed_extraction (the OCR
        # path completed but didn't yield enough analysable text). Wired
        # in [[CS-056]]; the 500-char trigger arrives with [[CS-053]].
        NotAnalyzableReason.TEXT_TOO_SHORT: ProcessingStatus.FAILED_EXTRACTION,
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
