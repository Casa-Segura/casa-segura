"""CorpusVersion activation flow (CS-090).

Activation is a singleton: at most one `CorpusVersion` row may have
`is_active=True`. The DB enforces this with a partial unique constraint
(`uq_corpus_version_active_singleton`), but the immutability trigger
from CS-030 allows `is_active` to flip. This module wraps the
deactivate-then-activate dance in a single transaction so callers don't
trip the partial unique constraint mid-flight.
"""

from __future__ import annotations

import structlog

from django.db import transaction

from corpus.infrastructure.django.models import CorpusVersion

logger = structlog.get_logger(__name__)


def latest_active() -> CorpusVersion | None:
    return CorpusVersion.objects.filter(is_active=True).first()


@transaction.atomic
def activate(version: str) -> CorpusVersion:
    """Mark `version` as the only active corpus version. Returns the row.

    Raises `CorpusVersion.DoesNotExist` if the version isn't loaded yet —
    callers are expected to call this AFTER `manage.py ingest_corpus`.
    """

    target = CorpusVersion.objects.select_for_update().get(pk=version)
    if not target.is_active:
        CorpusVersion.objects.filter(is_active=True).exclude(pk=version).update(is_active=False)
        target.is_active = True
        target.save(update_fields=["is_active"])
        logger.info("corpus.version.activated", version=version)
    return target


@transaction.atomic
def deactivate_all() -> int:
    """Drop the active flag on every version. Returns the count touched."""

    count = CorpusVersion.objects.filter(is_active=True).update(is_active=False)
    if count:
        logger.info("corpus.version.deactivate_all", count=count)
    return count
