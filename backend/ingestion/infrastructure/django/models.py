"""Ingestion: transient tables for the upload + OCR pipeline.

DOMAIN_MODEL §4.1, §4.2. Both tables auto-purge after `expires_at` (24h) via the
`platform.cleanup_transient` Celery beat job.

Privacy invariants enforced here:
    - `ContractSubmission` MUST NOT have an `extracted_text` column. Token count
      and language only. The actual text lives in-memory and flows through Redis
      Streams to F2 with TTL ≤ 300s (per GLOBAL_ASSUMPTIONS §13).
    - Original file bytes are never persisted to disk."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.db import models
from django.db.models import Q
from django.utils import timezone

from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    ExtractionStrategy,
    FileFormat,
    OcrJobStatus,
    ProcessingStatus,
    SubmissionSource,
)


def _transient_default_expiry() -> timezone.datetime:
    """Default expiry for transient ingestion rows: now + 24 hours."""
    return timezone.now() + timedelta(hours=24)


class ContractSubmission(models.Model):
    """Contract upload in processing. Transient (24h TTL) — DOMAIN §4.1.

    Privacy: NO `extracted_text` column. Only `extracted_text_token_count` and
    `extracted_text_language` for audit/observability."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission_hash = models.CharField(
        max_length=64,
        unique=True,
        help_text="SHA-256 of the original file (idempotency key)",
    )
    file_format = models.CharField(
        max_length=8,
        choices=FileFormat.choices,
        help_text="One of pdf|jpg|jpeg|png|heic|webp",
    )
    file_size_bytes = models.PositiveIntegerField(help_text="Size in bytes (pre-OCR)")
    file_count = models.PositiveSmallIntegerField(
        default=1,
        help_text="Number of files attached (1-50 per CS-025)",
    )
    page_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total page count once known (NULL for images)",
    )

    source = models.CharField(
        max_length=16,
        choices=SubmissionSource.choices,
        default=SubmissionSource.WEB,
        help_text="Channel the submission arrived on",
    )

    disclaimer_accepted_at = models.DateTimeField(help_text="When the user acknowledged the disclaimer (BR-07)")
    disclaimer_method = models.CharField(
        max_length=24,
        choices=DisclaimerAcceptanceMethod.choices,
        default=DisclaimerAcceptanceMethod.CHECKBOX,
        help_text="How the disclaimer was accepted",
    )

    received_at = models.DateTimeField(auto_now_add=True, help_text="When the file landed")
    processing_status = models.CharField(
        max_length=32,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.RECEIVED,
        help_text="Pipeline state",
    )
    extraction_strategy_attempted = models.CharField(
        max_length=16,
        choices=ExtractionStrategy.choices,
        null=True,
        blank=True,
        help_text="Last extraction strategy tried",
    )
    extraction_strategy_successful = models.CharField(
        max_length=16,
        choices=ExtractionStrategy.choices,
        null=True,
        blank=True,
        help_text="Extraction strategy that succeeded (NULL if all failed)",
    )

    extracted_text_token_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Audit-only count. The text itself is NEVER persisted.",
    )
    extracted_text_language = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        help_text="Detected ISO 639-1 code (e.g. 'es', 'en'). Non-Spanish triggers rejection.",
    )

    error_reason = models.TextField(blank=True, default="", help_text="Human-readable failure description")
    error_code = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Stable error code per CS-009 error envelope",
    )

    analysis = models.ForeignKey(
        "platform_core.ContractAnalysis",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="submissions",
        help_text="Set when the submission successfully produces an analysis (one-to-one in practice)",
    )

    expires_at = models.DateTimeField(
        default=_transient_default_expiry,
        help_text="Cleanup job purges rows past this timestamp (default +24h)",
    )

    class Meta:
        db_table = "contract_submission"
        verbose_name = "Contract Submission"
        verbose_name_plural = "Contract Submissions"
        constraints = [
            models.CheckConstraint(
                check=Q(file_count__gte=1) & Q(file_count__lte=50),
                name="ck_submission_file_count_1_50",
            ),
            models.CheckConstraint(
                check=Q(processing_status__in=[s.value for s in ProcessingStatus]),
                name="ck_submission_processing_status_enum",
            ),
        ]
        indexes = [
            models.Index(fields=["submission_hash"], name="idx_submission_hash"),
            models.Index(fields=["processing_status"], name="idx_submission_status"),
            models.Index(fields=["expires_at"], name="idx_submission_expires"),
            models.Index(fields=["analysis"], name="idx_submission_analysis"),
        ]

    def __str__(self) -> str:
        return f"ContractSubmission({self.id}, {self.processing_status})"


class OcrJob(models.Model):
    """Individual text-extraction attempt. Provides observability and retry (DOMAIN §4.2).

    Multiple jobs may exist per submission (one per attempt of each strategy).
    Status enum follows PRD DDL (success|failed|timeout|cancelled), with `running`
    added for in-flight orchestrator tracking (see CS-025 notes)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission = models.ForeignKey(
        ContractSubmission,
        on_delete=models.CASCADE,
        related_name="ocr_jobs",
        help_text="Parent submission",
    )
    strategy = models.CharField(
        max_length=16,
        choices=ExtractionStrategy.choices,
        help_text="Strategy used in this attempt",
    )
    started_at = models.DateTimeField(auto_now_add=True, help_text="When the job started")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the job finished (NULL while running)")
    status = models.CharField(
        max_length=16,
        choices=OcrJobStatus.choices,
        default=OcrJobStatus.RUNNING,
        help_text="Outcome",
    )
    error = models.TextField(blank=True, default="", help_text="Truncated error message on failure")
    error_code = models.CharField(max_length=64, blank=True, default="", help_text="Stable error code")
    tokens_consumed = models.PositiveIntegerField(
        null=True, blank=True, help_text="LLM tokens spent (vision_llm only)"
    )
    cost_estimate_cents = models.PositiveIntegerField(
        null=True, blank=True, help_text="Estimated call cost in USD cents"
    )
    attempt_number = models.PositiveSmallIntegerField(default=1, help_text="Attempt counter for this strategy")
    expires_at = models.DateTimeField(
        default=_transient_default_expiry,
        help_text="Cleanup job purges rows past this timestamp (default +24h)",
    )

    class Meta:
        db_table = "ocr_job"
        verbose_name = "OCR Job"
        verbose_name_plural = "OCR Jobs"
        constraints = [
            models.CheckConstraint(
                check=Q(strategy__in=[s.value for s in ExtractionStrategy]),
                name="ck_ocr_job_strategy_enum",
            ),
            models.CheckConstraint(
                check=Q(status__in=[s.value for s in OcrJobStatus]),
                name="ck_ocr_job_status_enum",
            ),
        ]
        indexes = [
            models.Index(fields=["submission", "started_at"], name="idx_ocr_job_submission"),
            models.Index(fields=["status"], name="idx_ocr_job_status"),
            models.Index(fields=["expires_at"], name="idx_ocr_job_expires"),
        ]

    def __str__(self) -> str:
        return f"OcrJob({self.id}, {self.strategy}, {self.status})"
