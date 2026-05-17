"""Pure retention job runners (invoked by Celery tasks and ``run_retention_job`` CLI).

See ADR-0005 and tickets CS-271 / CS-272 / CS-274 / CS-273 / CS-275.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from delivery.domain.enums import DeliveryRequestStatus
from delivery.infrastructure.django.models import DeliveryRequest
from ingestion.domain.enums import ProcessingStatus
from ingestion.infrastructure.django.models import ContractSubmission
from platform_core.domain.enums import DeliveryStatus
from platform_core.infrastructure.django.models import ContractAnalysis

logger = logging.getLogger(__name__)


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


def run_anonymize_old_analyses() -> int:
    """Placeholder until CS-273 implements US-07/US-08 anonymization."""
    logger.warning(
        "retention_job_not_implemented",
        extra={"job_name": "anonymize_old_analyses"},
    )
    return 0


def run_recompute_project_metrics() -> int:
    """Placeholder until CS-275 implements hourly project aggregates."""
    logger.warning(
        "retention_job_not_implemented",
        extra={"job_name": "recompute_project_metrics"},
    )
    return 0
