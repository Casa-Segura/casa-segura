"""BenchmarkVersion activation flow (CS-130 / CS-136).

Mirrors the singleton pattern from `corpus.application.version`: at most one
`BenchmarkVersion` row may have `is_active=True`, enforced by the partial unique
index `uq_benchmark_version_active_singleton`. The catalog-immutability trigger
attached in `economics/migrations/0002_attach_immutability.py` permits only
`is_active` to flip after publish.
"""

from __future__ import annotations

from datetime import date

import structlog
from django.db import transaction
from django.utils import timezone

from economics.infrastructure.django.models import BenchmarkVersion

logger = structlog.get_logger(__name__)


def latest_active() -> BenchmarkVersion | None:
    return BenchmarkVersion.objects.filter(is_active=True).first()


@transaction.atomic
def activate(version: str) -> BenchmarkVersion:
    """Mark `version` as the only active benchmark version. Returns the row.

    Raises `BenchmarkVersion.DoesNotExist` if the version isn't loaded yet —
    callers are expected to call this AFTER `manage.py load_benchmark_catalog`.
    """

    target = BenchmarkVersion.objects.select_for_update().get(pk=version)
    if not target.is_active:
        BenchmarkVersion.objects.filter(is_active=True).exclude(pk=version).update(
            is_active=False
        )
        target.is_active = True
        target.save(update_fields=["is_active"])
        logger.info("benchmark.version.activated", version=version)
    return target


@transaction.atomic
def deactivate_all() -> int:
    """Drop the active flag on every version. Returns the count touched."""

    count = BenchmarkVersion.objects.filter(is_active=True).update(is_active=False)
    if count:
        logger.info("benchmark.version.deactivate_all", count=count)
    return count


def assert_freshness(version: BenchmarkVersion | None, *, today: date | None = None) -> None:
    """Emit a structured warning if the active benchmark catalog is past its review window.

    PRD_F5 BR-12: expired benchmarks must surface an operational alert but MUST
    NOT block analysis. This helper centralizes the log signal so CS-136 can
    wire it without scattering date arithmetic across callers.
    """

    if version is None:
        return
    reference = today or timezone.now().date()
    # The freshest `next_review_due` across all rows for this version is the
    # one most relevant to staleness — but `BenchmarkVersion` itself does not
    # carry that field, so we pick the minimum across child rows.
    next_review = (
        version.benchmarks.values_list("next_review_due", flat=True).order_by("next_review_due").first()
    )
    if next_review is None:
        return
    if reference > next_review:
        logger.warning(
            "benchmark.version.stale",
            version=version.version,
            next_review_due=next_review.isoformat(),
            days_past_due=(reference - next_review).days,
        )
