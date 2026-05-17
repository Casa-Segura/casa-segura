"""Manual retention job runner — ADR-0005 §Manual / ops invokes."""

from __future__ import annotations

from collections.abc import Callable

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from platform_core.worker.retention import runners
from platform_core.worker.retention.metrics import run_retention_job_safe
from platform_core.worker.retention.tasks import (
    TASK_ANONYMIZE,
    TASK_CLEANUP_DELIVERY_TARGETS,
    TASK_CLEANUP_TRANSIENT,
    TASK_EXPIRE_LINKS,
    TASK_RECOMPUTE_PROJECT,
)


def _registered_jobs() -> dict[str, Callable[[], int]]:
    return {
        "cleanup_transient": lambda: run_retention_job_safe(
            TASK_CLEANUP_TRANSIENT,
            "cleanup_transient",
            lambda: runners.run_cleanup_transient(batch_size=settings.JOB_BATCH_SIZE),
        ),
        "cleanup_delivery_targets": lambda: run_retention_job_safe(
            TASK_CLEANUP_DELIVERY_TARGETS,
            "cleanup_delivery_targets",
            lambda: runners.run_cleanup_delivery_targets(
                grace_seconds=settings.DELIVERY_TARGET_ERASE_GRACE_SECONDS,
            ),
        ),
        "expire_links": lambda: run_retention_job_safe(
            TASK_EXPIRE_LINKS,
            "expire_links",
            runners.run_expire_links,
        ),
        "anonymize_old_analyses": lambda: run_retention_job_safe(
            TASK_ANONYMIZE,
            "anonymize_old_analyses",
            runners.run_anonymize_old_analyses,
        ),
        "recompute_project_metrics": lambda: run_retention_job_safe(
            TASK_RECOMPUTE_PROJECT,
            "recompute_project_metrics",
            runners.run_recompute_project_metrics,
        ),
    }


class Command(BaseCommand):
    help = "Run a single PRD F8 retention job (ADR-0005). Exit 1 on failure."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "job_name",
            choices=sorted(_registered_jobs().keys()),
            help="Retention job snake_case identifier",
        )

    def handle(self, *args, **options) -> None:
        job_name = options["job_name"]
        runner = _registered_jobs()[job_name]
        try:
            count = runner()
        except Exception as exc:
            raise CommandError(f"{job_name} failed: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"{job_name}: records_processed={count}"))
