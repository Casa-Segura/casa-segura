"""platform_core: shared schema and operational tables.

Models declared by F8 (PRD_F8_PERSISTENCIA_PROYECTO_RETENCION + DOMAIN_MODEL §3.1, §3.2):
    - Project: persistent, indefinite. Aggregation unit per real estate project.
    - ContractAnalysis: persistent, 90-day full + indefinite anonymized. Central entity.
    - PrivacyAuditLog: append-only audit trail for retention/anonymization events.
    - JobExecutionLog: observability for Celery beat / retention jobs.

Renamed from `platform/` to `platform_core/` to avoid stdlib import collision (ADR-0002)."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q
from django.utils import timezone

from common.infrastructure.django.models import ModelWithTimeStamps
from platform_core.domain.enums import (
    Band,
    ContractType,
    DeliveryChannel,
    DeliveryStatus,
    JobExecutionStatus,
    PrivacyAuditEvent,
)
from platform_core.domain.pii import PIIDetected, assert_no_pii


def _audit_default_expiry() -> timezone.datetime:
    """Default expiry for privacy audit log rows: 1 year."""
    return timezone.now() + timedelta(days=365)


def _job_log_default_expiry() -> timezone.datetime:
    """Default expiry for job execution log rows: 30 days."""
    return timezone.now() + timedelta(days=30)


class Project(ModelWithTimeStamps):
    """Real estate project, the system's unit of aggregate intelligence (DOMAIN §3.1).

    Created on the first analysis whose `project_name_normalized` does not match any
    existing project. Never deleted, even after its individual analyses are anonymized."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_name = models.TextField(help_text="Name as it typically appears in contracts")
    normalized_name = models.TextField(
        unique=True,
        help_text="Normalized slug used as the matching key for incoming analyses",
    )
    first_seen = models.DateTimeField(
        auto_now_add=True,
        help_text="When the project was first created in the system",
    )
    last_analyzed = models.DateTimeField(help_text="Last time an analysis was associated with this project")
    total_analyses = models.PositiveIntegerField(default=0, help_text="Count of analyses associated (denormalized)")
    avg_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Moving average of associated total scores (recomputed by retention job)",
    )
    score_distribution = models.JSONField(
        default=dict,
        blank=True,
        help_text="Count by band: {green: N, yellow: M, red: K}",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extensible; must never contain PII",
    )
    last_recomputed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When avg_score / score_distribution were last recomputed",
    )

    class Meta:
        db_table = "project"
        verbose_name = "Project"
        verbose_name_plural = "Projects"
        indexes = [
            models.Index(fields=["normalized_name"], name="idx_project_normalized"),
            models.Index(fields=["last_analyzed"], name="idx_project_last_analyzed"),
        ]

    def __str__(self) -> str:
        return f"Project({self.normalized_name})"

    def clean(self) -> None:
        """Reject any metadata payload that contains PII (CS-023, DOMAIN §3.1).

        Raises ValidationError so DRF / forms surface a clean 400 instead
        of a 500. The underlying PIIDetected carries the offending path."""
        super().clean()
        try:
            assert_no_pii(self.metadata)
        except PIIDetected as exc:
            from django.core.exceptions import (  # noqa: PLC0415 — break circular import between core models and Django exceptions
                ValidationError,
            )

            raise ValidationError({"metadata": str(exc)}) from exc

    def save(self, *args, **kwargs) -> None:
        """Default `last_analyzed` to `first_seen` (or now()) on insert path."""
        if self.last_analyzed is None:
            self.last_analyzed = self.first_seen or timezone.now()
        self.full_clean(exclude={"first_seen"})
        return super().save(*args, **kwargs)


class ContractAnalysis(ModelWithTimeStamps):
    """Result of the rubric applied to a specific contract — system's central entity (DOMAIN §3.2).

    Lifecycle:
        - Stub created at submission time with `delivery_status=pending`; rubric fields
          (`score_total`, `band`, etc.) start NULL and are populated when F4 finalizes.
        - 90-day retention: anonymization job nulls/buckets sensitive fields and sets
          `anonymized_at`; `submission_hash` survives for future deduplication.

    Notes:
        - `score_total` is nullable until rubric completes (F8 model choice; reconciled
          with DOMAIN §3.2 by accepting NULL during the pre-finalize window).
        - `override_triggered` is a Postgres ArrayField, not JSONB (per F8 §5).
        - `delivery_status` value set is canonical per PRD_F8 §5.1 (supersedes
          RUBRICA_CONTRATO.md §12.2)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_short_id = models.CharField(
        max_length=24,
        unique=True,
        help_text="Public-facing short ID, format CS-YYYY-XXXXXX",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.PROTECT,
        related_name="analyses",
        help_text="Project this analysis is associated with",
    )

    contract_type = models.CharField(
        max_length=16,
        choices=ContractType.choices,
        help_text="Final detected contract type",
    )
    contract_type_declared = models.CharField(
        max_length=16,
        choices=ContractType.choices,
        null=True,
        blank=True,
        help_text="Type the document claims to be (may differ if reclassified)",
    )
    contract_type_reclassified = models.BooleanField(default=False, help_text="Whether reclassification occurred (F2)")
    reclassification_reason = models.TextField(
        blank=True,
        default="",
        help_text="Justification for reclassification, citing indicators",
    )

    score_total = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
        help_text="Final score 0-10. NULL while rubric pending; populated by F4 finalize.",
    )
    band = models.CharField(
        max_length=16,
        choices=Band.choices,
        null=True,
        blank=True,
        help_text="Final band (NULL until rubric completes)",
    )
    override_triggered = ArrayField(
        models.CharField(max_length=64),
        default=list,
        blank=True,
        help_text="List of active override codes (F4 fills)",
    )
    scores_by_category = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of CategoryScore (DOMAIN §5.1)",
    )
    criterion_evaluations = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of CriterionEvaluation (DOMAIN §5.2); reduced to per-category aggregate at anonymization",
    )
    findings = models.JSONField(
        default=list,
        blank=True,
        help_text="Array of Finding (DOMAIN §5.3); reduced to severity counts at anonymization",
    )
    findings_count = models.PositiveIntegerField(default=0, help_text="Total findings (denormalized)")
    critical_findings_count = models.PositiveIntegerField(default=0, help_text="Count of `critical` severity findings")
    unverifiable_count = models.PositiveIntegerField(default=0, help_text="Count of unverifiable criteria")

    executive_summary = models.TextField(
        blank=True,
        default="",
        help_text="F4 synthesized verdict narrative; preserved after anonymization (PRD F8 US-07)",
    )

    economic_summary = models.JSONField(
        null=True,
        blank=True,
        help_text="EconomicSummary (DOMAIN §5.5); bucketed at anonymization",
    )

    rubric_version = models.ForeignKey(
        "rubric.RubricVersion",
        on_delete=models.PROTECT,
        related_name="analyses",
        db_column="rubric_version",
        to_field="version",
        help_text="Rubric version used (PROTECT: catalog rows cannot be deleted while referenced)",
    )
    corpus_version = models.ForeignKey(
        "corpus.CorpusVersion",
        on_delete=models.PROTECT,
        related_name="analyses",
        db_column="corpus_version",
        to_field="version",
        help_text="Corpus version used",
    )
    benchmark_version = models.ForeignKey(
        "economics.BenchmarkVersion",
        on_delete=models.PROTECT,
        related_name="analyses",
        db_column="benchmark_version",
        to_field="version",
        null=True,
        blank=True,
        help_text="Benchmark version used (nullable for contract types that skip economics)",
    )

    delivery_status = models.CharField(
        max_length=16,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        help_text="Report delivery state (canonical per PRD_F8 §5.1)",
    )
    delivery_channel = models.CharField(
        max_length=24,
        choices=DeliveryChannel.choices,
        null=True,
        blank=True,
        help_text="Channel chosen by the user",
    )
    delivery_target_hash = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Salt+SHA-256 hash of email or phone; erased at anonymization",
    )
    link_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Web link expiration (LINK_TTL_DAYS=30 default)",
    )
    resend_count = models.PositiveSmallIntegerField(
        default=0,
        help_text="Number of resend attempts (capped at 3 in service layer)",
    )

    anonymized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="If anonymized, when",
    )
    submission_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 of the original contract (idempotency; preserved after anonymization)",
    )

    classification_confidence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="F2 §5.1: confidence of the accepted classification (NULL until classifier runs)",
    )
    classification_attempts = models.PositiveSmallIntegerField(
        default=0,
        help_text="F2 §5.1: 0 pre-run, 1 single call, 2 if §8.3 validator fired",
    )
    elements_detected = models.JSONField(
        default=dict,
        blank=True,
        help_text="F2 §5.1 / US-05: structural boolean flags (public_deed, arbitration_clause, …)",
    )
    reclassification_indicators = models.JSONField(
        null=True,
        blank=True,
        help_text="F2 §8.4 envelope {indicators, count, severity}; NULL when leasing detector did not run",
    )
    project_name_canonical = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="F2 §5.1 raw canonical project name as extracted (pre-normalization)",
    )
    economic_fields_raw = models.JSONField(
        null=True,
        blank=True,
        help_text="F2 §8.5 coerced extraction payload; NULL for non-economic contract types",
    )

    class Meta:
        db_table = "contract_analysis"
        verbose_name = "Contract Analysis"
        verbose_name_plural = "Contract Analyses"
        constraints = [
            models.CheckConstraint(
                check=Q(score_total__isnull=True) | (Q(score_total__gte=0) & Q(score_total__lte=10)),
                name="ca_score_range",
            ),
            models.CheckConstraint(
                check=Q(band__isnull=True) | Q(band__in=[b.value for b in Band]),
                name="ck_contract_analysis_band_enum",
            ),
            models.CheckConstraint(
                check=Q(delivery_status__in=[s.value for s in DeliveryStatus]),
                name="ck_contract_analysis_delivery_status_enum",
            ),
            models.CheckConstraint(
                check=(
                    Q(classification_confidence__isnull=True)
                    | (Q(classification_confidence__gte=0) & Q(classification_confidence__lte=1))
                ),
                name="ck_contract_analysis_classification_confidence_range",
            ),
            models.CheckConstraint(
                check=Q(classification_attempts__lte=3),
                name="ck_contract_analysis_classification_attempts_max",
            ),
        ]
        indexes = [
            models.Index(fields=["project"], name="idx_analysis_project"),
            models.Index(fields=["public_short_id"], name="idx_analysis_short_id"),
            models.Index(fields=["submission_hash"], name="idx_analysis_subhash"),
            models.Index(fields=["created_at"], name="idx_analysis_created"),
            models.Index(
                fields=["link_expires_at"],
                name="idx_analysis_link_exp",
                condition=Q(link_expires_at__isnull=False),
            ),
            models.Index(
                fields=["anonymized_at"],
                name="idx_analysis_anon",
                condition=Q(anonymized_at__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        return f"ContractAnalysis({self.public_short_id})"


class PrivacyAuditLog(models.Model):
    """Append-only audit trail for privacy-affecting events (F8 §5).

    Created by retention/anonymization jobs and user-initiated resends. Auto-purged
    after `expires_at` (default +1 year) by the audit-log cleanup job."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(
        max_length=64,
        choices=PrivacyAuditEvent.choices,
        help_text="What kind of privacy event was recorded",
    )
    related_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="ID of the affected row (e.g. analysis_id) if applicable",
    )
    related_table = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Table the related_id belongs to",
    )
    event_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Additional structured context; must not contain PII",
    )
    triggered_by = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        help_text="Actor/process that triggered the event (job name, capability holder hash, etc.)",
    )
    occurred_at = models.DateTimeField(auto_now_add=True, help_text="When the event was logged")
    expires_at = models.DateTimeField(
        default=_audit_default_expiry,
        help_text="When this row may be purged (default: occurred_at + 1 year)",
    )

    class Meta:
        db_table = "privacy_audit_log"
        verbose_name = "Privacy Audit Log Entry"
        verbose_name_plural = "Privacy Audit Log"
        constraints = [
            models.CheckConstraint(
                check=Q(event_type__in=[e.value for e in PrivacyAuditEvent]),
                name="ck_privacy_audit_event_enum",
            ),
        ]
        indexes = [
            models.Index(fields=["event_type"], name="idx_audit_event"),
            models.Index(fields=["occurred_at"], name="idx_audit_occurred"),
            models.Index(fields=["expires_at"], name="idx_audit_expires"),
        ]

    def __str__(self) -> str:
        return f"PrivacyAuditLog({self.event_type}, {self.occurred_at})"


class JobExecutionLog(models.Model):
    """Observability for Celery beat / retention jobs (F8 §5).

    Each scheduled job writes one row at completion with status + counts."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_name = models.CharField(max_length=128, help_text="Celery task name (e.g. platform.anonymize_old_analyses)")
    started_at = models.DateTimeField(auto_now_add=True, help_text="When the job started")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="When the job ended (NULL if still running)")
    status = models.CharField(
        max_length=16,
        choices=JobExecutionStatus.choices,
        help_text="Outcome",
    )
    records_processed = models.IntegerField(null=True, blank=True, help_text="Records touched by this run")
    error_message = models.TextField(blank=True, default="", help_text="Truncated error trail for failures")
    expires_at = models.DateTimeField(
        default=_job_log_default_expiry,
        help_text="When this row may be purged (default: started_at + 30 days)",
    )

    class Meta:
        db_table = "job_execution_log"
        verbose_name = "Job Execution Log Entry"
        verbose_name_plural = "Job Execution Log"
        indexes = [
            models.Index(fields=["job_name", "started_at"], name="idx_jobs_started"),
            models.Index(fields=["expires_at"], name="idx_jobs_expires"),
        ]

    def __str__(self) -> str:
        return f"JobExecutionLog({self.job_name}, {self.status}, {self.started_at})"
