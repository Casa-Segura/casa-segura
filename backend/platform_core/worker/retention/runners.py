"""Pure retention job runners (invoked by Celery tasks and ``run_retention_job`` CLI).

See ADR-0005 and tickets CS-271 / CS-272 / CS-274 / CS-273 / CS-275.
"""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Avg, Count, F, Q
from django.utils import timezone

from delivery.domain.enums import DeliveryRequestStatus
from delivery.infrastructure.django.models import DeliveryRequest
from ingestion.domain.enums import ProcessingStatus
from ingestion.infrastructure.django.models import ContractSubmission
from platform_core.domain.enums import Band, DeliveryStatus, PrivacyAuditEvent
from platform_core.infrastructure.django.models import ContractAnalysis, PrivacyAuditLog, Project
from platform_core.worker.retention import anonymization

logger = logging.getLogger(__name__)

_DIST_KEYS = ("green", "yellow", "red", "not_analyzable")


def run_cleanup_transient(*, batch_size: int) -> int:
    """Delete expired ``ContractSubmission`` rows (CS-271).

    ``OcrJob`` rows cascade from submission. Rows linked to an ``analysis`` FK
    are kept until ``processing_status == completed`` so in-flight pipelines are
    not purged mid-flight.
    """

    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    guard_open_pipeline = Q(analysis__isnull=False) & ~Q(processing_status=ProcessingStatus.COMPLETED.value)
    total_submissions = 0
    while True:
        eligible = (
            ContractSubmission.objects.filter(expires_at__lt=timezone.now())
            .exclude(guard_open_pipeline)
            .order_by("pk")
            .values_list("pk", flat=True)[:batch_size]
        )
        ids = list(eligible)
        if not ids:
            break
        _, deleted_detail = ContractSubmission.objects.filter(pk__in=ids).delete()
        chunk = deleted_detail.get(ContractSubmission._meta.label, len(ids))
        total_submissions += chunk
    return total_submissions


def run_cleanup_delivery_targets(*, grace_seconds: int) -> int:
    """Clear encrypted delivery destinations past grace / TTL (CS-272).

    Never clears ``target_hash`` (required for guarded resend).
    """

    if grace_seconds < 0:
        raise ValueError("grace_seconds must be non-negative")

    now = timezone.now()
    grace_cutoff = now - timedelta(seconds=grace_seconds)

    delivered_branch = (
        Q(status=DeliveryRequestStatus.DELIVERED.value)
        & Q(target_value_encrypted__isnull=False)
        & Q(delivered_at__lte=grace_cutoff)
    )
    expired_branch = Q(expires_at__lt=now) & Q(target_value_encrypted__isnull=False)

    return DeliveryRequest.objects.filter(delivered_branch | expired_branch).update(
        target_value_encrypted=None,
    )


def run_expire_links() -> int:
    """Mark analyses whose public link TTL elapsed as ``expired`` (CS-274)."""

    now = timezone.now()
    return ContractAnalysis.objects.filter(
        link_expires_at__lt=now,
        delivery_status__in=(
            DeliveryStatus.AVAILABLE_LINK.value,
            DeliveryStatus.SENT_EMAIL.value,
            DeliveryStatus.SENT_SMS.value,
        ),
    ).update(delivery_status=DeliveryStatus.EXPIRED.value)


def run_anonymize_old_analyses(*, batch_size: int, policy_days: int) -> int:
    """Anonymize analyses past ``policy_days`` (CS-273); audit rows (CS-276) same transaction."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if policy_days < 1:
        raise ValueError("policy_days must be positive")

    cutoff = timezone.now() - timedelta(days=policy_days)
    processed = 0
    attempted: set[uuid.UUID] = set()

    while True:
        chunk_ids = list(
            ContractAnalysis.objects.filter(anonymized_at__isnull=True, created_at__lt=cutoff)
            .exclude(pk__in=attempted)
            .order_by("pk")
            .values_list("pk", flat=True)[:batch_size]
        )
        if not chunk_ids:
            break
        for analysis_id in chunk_ids:
            attempted.add(analysis_id)
            try:
                processed += _anonymize_single_analysis(analysis_id, policy_days=policy_days)
            except Exception:
                logger.exception(
                    "retention_anonymize_row_failed",
                    extra={"analysis_id": str(analysis_id)},
                )
    return processed


def _anonymize_single_analysis(analysis_id, *, policy_days: int) -> int:
    """Return 1 if anonymized, 0 if skipped."""

    with transaction.atomic():
        locked = (
            ContractAnalysis.objects.select_for_update()
            .filter(pk=analysis_id, anonymized_at__isnull=True)
            .first()
        )
        if locked is None:
            return 0

        findings_removed = len(locked.findings or [])
        criterion_rows_removed = len(locked.criterion_evaluations or [])
        raw_econ = locked.economic_summary if isinstance(locked.economic_summary, dict) else None

        locked.delivery_target_hash = None
        locked.criterion_evaluations = []
        locked.findings = []
        locked.scores_by_category = anonymization.reduce_scores_by_category(locked.scores_by_category or [])
        locked.economic_summary = anonymization.anonymize_economic_summary(raw_econ)
        locked.anonymized_at = timezone.now()

        locked.save(
            update_fields=[
                "delivery_target_hash",
                "criterion_evaluations",
                "findings",
                "scores_by_category",
                "economic_summary",
                "anonymized_at",
                "updated_at",
            ]
        )

        PrivacyAuditLog.objects.create(
            event_type=PrivacyAuditEvent.ANALYSIS_ANONYMIZED.value,
            related_id=locked.pk,
            related_table=ContractAnalysis._meta.db_table,
            triggered_by="job:anonymize_old_analyses",
            event_data={
                "policy_days": policy_days,
                "findings_removed": findings_removed,
                "criterion_rows_removed": criterion_rows_removed,
            },
        )
    return 1


def _avg_close(a: Decimal | None, b: Decimal | None) -> bool:
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= Decimal("0.05")


def _normalized_distribution(dist: dict | None) -> dict[str, int]:
    base = {k: 0 for k in _DIST_KEYS}
    if not isinstance(dist, dict):
        return base
    for k in _DIST_KEYS:
        try:
            base[k] = int(dist.get(k, 0))
        except (TypeError, ValueError):
            base[k] = 0
    return base


def run_recompute_project_metrics(*, batch_size: int) -> int:
    """Recompute ``Project`` aggregates for stale rows (CS-275)."""

    if batch_size < 1:
        raise ValueError("batch_size must be positive")

    updates = 0
    while True:
        candidate_ids = list(
            Project.objects.filter(
                Q(last_recomputed_at__isnull=True) | Q(last_recomputed_at__lt=F("last_analyzed"))
            )
            .exclude(metadata__contains={"placeholder": True})
            .order_by("pk")
            .values_list("pk", flat=True)[:batch_size]
        )
        if not candidate_ids:
            break

        for project_id in candidate_ids:
            try:
                updates += _recompute_single_project(project_id)
            except Exception:
                logger.exception(
                    "retention_recompute_project_failed",
                    extra={"project_id": str(project_id)},
                )
    return updates


def _recompute_single_project(project_id, *, force: bool = False) -> int:
    """Return 1 if aggregate columns changed; 0 if only timestamp alignment or no-op."""

    with transaction.atomic():
        project = Project.objects.select_for_update().filter(pk=project_id).first()
        if project is None:
            return 0
        if (
            not force
            and project.last_recomputed_at is not None
            and project.last_recomputed_at >= project.last_analyzed
        ):
            return 0

        agg = ContractAnalysis.objects.filter(project_id=project_id).aggregate(
            avg_score=Avg("score_total"),
            n=Count("id"),
            green=Count("id", filter=Q(band=Band.GREEN.value)),
            yellow=Count("id", filter=Q(band=Band.YELLOW.value)),
            red=Count("id", filter=Q(band=Band.RED.value)),
            not_analyzable=Count("id", filter=Q(band=Band.NOT_ANALYZABLE.value)),
        )

        n_analyses = int(agg["n"] or 0)
        new_dist = {
            "green": int(agg["green"] or 0),
            "yellow": int(agg["yellow"] or 0),
            "red": int(agg["red"] or 0),
            "not_analyzable": int(agg["not_analyzable"] or 0),
        }
        raw_avg = agg["avg_score"]
        new_avg: Decimal | None
        if raw_avg is None or n_analyses == 0:
            new_avg = None
        else:
            new_avg = Decimal(str(raw_avg)).quantize(Decimal("0.1"))

        old_avg = project.avg_score
        old_dist_norm = _normalized_distribution(project.score_distribution)
        new_dist_norm = _normalized_distribution(new_dist)

        same_avg = _avg_close(old_avg, new_avg)
        same_dist = old_dist_norm == new_dist_norm
        same_total = int(project.total_analyses or 0) == n_analyses

        if same_avg and same_dist and same_total:
            project.last_recomputed_at = timezone.now()
            project.save(update_fields=["last_recomputed_at", "updated_at"])
            return 0

        project.avg_score = new_avg
        project.score_distribution = new_dist
        project.total_analyses = n_analyses
        project.last_recomputed_at = timezone.now()
        project.save(
            update_fields=[
                "avg_score",
                "score_distribution",
                "total_analyses",
                "last_recomputed_at",
                "updated_at",
            ]
        )
    return 1


def recompute_metrics_for_project(project_id, *, force: bool = True) -> int:
    """Repair metrics for one project (e.g. placeholder excluded from global sweep).

    Uses ``force=True`` so ops can refresh a UUID even when timestamps look fresh.
    """

    return _recompute_single_project(project_id, force=force)
