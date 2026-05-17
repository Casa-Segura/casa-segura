"""Structured observability + ``JobExecutionLog`` writes for retention jobs (ADR-0005 BR-13)."""

from __future__ import annotations

from collections.abc import Callable

import structlog

from django.utils import timezone

from platform_core.domain.enums import JobExecutionStatus
from platform_core.infrastructure.django.models import JobExecutionLog

logger = structlog.get_logger(__name__)


def run_retention_job_safe(celery_task_name: str, logical_job_key: str, runner: Callable[[], int]) -> int:
    """Execute ``runner``, emitting structured logs + ``JobExecutionLog`` (no row payloads)."""

    started_at = timezone.now()
    try:
        count = runner()
        completed_at = timezone.now()
        logger.info(
            "retention_job",
            job_name=logical_job_key,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            status="success",
            records_processed=count,
        )
        JobExecutionLog.objects.create(
            job_name=celery_task_name,
            completed_at=completed_at,
            status=JobExecutionStatus.SUCCESS.value,
            records_processed=count,
            error_message="",
        )
        return count
    except Exception as exc:
        completed_at = timezone.now()
        err = str(exc)
        logger.error(
            "retention_job",
            job_name=logical_job_key,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            status="failed",
            records_processed=-1,
            error_code=type(exc).__name__,
            error_message=err[:512],
        )
        JobExecutionLog.objects.create(
            job_name=celery_task_name,
            completed_at=completed_at,
            status=JobExecutionStatus.FAILED.value,
            records_processed=-1,
            error_message=err[:2000],
        )
        raise
