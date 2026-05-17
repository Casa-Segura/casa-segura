"""Celery periodic tasks for PRD F8 retention jobs (ADR-0005)."""

from __future__ import annotations

from celery import shared_task

from django.conf import settings

from platform_core.worker.retention import runners
from platform_core.worker.retention.metrics import run_retention_job_safe

TASK_CLEANUP_TRANSIENT = "platform.cleanup_transient"
TASK_CLEANUP_DELIVERY_TARGETS = "platform.cleanup_delivery_targets"
TASK_EXPIRE_LINKS = "platform.expire_links"
TASK_ANONYMIZE = "platform.anonymize_old_analyses"
TASK_RECOMPUTE_PROJECT = "platform.recompute_project_metrics"


@shared_task(name=TASK_CLEANUP_TRANSIENT)
def cleanup_transient_task() -> int:
    return run_retention_job_safe(
        TASK_CLEANUP_TRANSIENT,
        "cleanup_transient",
        lambda: runners.run_cleanup_transient(batch_size=settings.JOB_BATCH_SIZE),
    )


@shared_task(name=TASK_CLEANUP_DELIVERY_TARGETS)
def cleanup_delivery_targets_task() -> int:
    return run_retention_job_safe(
        TASK_CLEANUP_DELIVERY_TARGETS,
        "cleanup_delivery_targets",
        lambda: runners.run_cleanup_delivery_targets(
            grace_seconds=settings.DELIVERY_TARGET_ERASE_GRACE_SECONDS,
        ),
    )


@shared_task(name=TASK_EXPIRE_LINKS)
def expire_links_task() -> int:
    return run_retention_job_safe(
        TASK_EXPIRE_LINKS,
        "expire_links",
        runners.run_expire_links,
    )


@shared_task(name=TASK_ANONYMIZE)
def anonymize_old_analyses_task() -> int:
    """Daily anonymization (CS-273) + privacy audit rows (CS-276)."""

    return run_retention_job_safe(
        TASK_ANONYMIZE,
        "anonymize_old_analyses",
        lambda: runners.run_anonymize_old_analyses(
            batch_size=settings.JOB_BATCH_SIZE,
            policy_days=settings.ANONYMIZATION_AFTER_DAYS,
        ),
    )


@shared_task(name=TASK_RECOMPUTE_PROJECT)
def recompute_project_metrics_task() -> int:
    """Hourly project aggregates (CS-275)."""

    return run_retention_job_safe(
        TASK_RECOMPUTE_PROJECT,
        "recompute_project_metrics",
        lambda: runners.run_recompute_project_metrics(batch_size=settings.JOB_BATCH_SIZE),
    )


__all__ = [
    "TASK_ANONYMIZE",
    "TASK_CLEANUP_DELIVERY_TARGETS",
    "TASK_CLEANUP_TRANSIENT",
    "TASK_EXPIRE_LINKS",
    "TASK_RECOMPUTE_PROJECT",
    "anonymize_old_analyses_task",
    "cleanup_delivery_targets_task",
    "cleanup_transient_task",
    "expire_links_task",
    "recompute_project_metrics_task",
]
