"""Project linkage service (CS-112 — implements CS-031 AC4 / PRD_F8 US-02).

Resolves a :class:`ProjectNameExtraction` into a concrete `Project` row
and returns a :class:`ProjectLinkResult` describing the action taken.

Collision policy (CS-031 AC4 + PRD_F8_PERSISTENCIA_PROYECTO_RETENCION
US-02 + BR-07)
------------------------------------------------------------------------

Two distinct behaviours, gated by ``ProjectNameExtraction.is_placeholder``:

1. **Placeholder path (``is_placeholder=True``).** ALWAYS INSERT a fresh
   `Project` row. Placeholders MUST NEVER be deduped (PRD_F8 BR-07: "each
   submission with an unextractable name creates its own placeholder").
   The `metadata.placeholder` flag is set to ``True`` so the retention
   job can exclude these rows from global aggregate metrics (PRD_F8 §3
   US-09).

2. **Real-name path (``is_placeholder=False``).** UPSERT keyed by
   `Project.normalized_name`:

   * If a row with that ``normalized_name`` already exists → return it,
     refreshing ``last_analyzed = NOW()`` (PRD_F8 US-02 acceptance
     criterion: "If `normalized_name` already exists: updates
     `last_analyzed`"). The ``canonical_name`` is left untouched in this
     implementation pass — the "preserve the more recent name" rule from
     PRD_F8 US-02 will land alongside the recompute job (CS owned by
     EPIC-04 follow-up).
   * Otherwise → INSERT a fresh row with the extracted ``raw`` text as
     ``canonical_name`` (falling back to the normalized form when ``raw``
     is ``None``).

The whole operation runs inside ``transaction.atomic()`` so a concurrent
insert with the same ``normalized_name`` cannot create a duplicate. We
guard against the unique-constraint race by catching `IntegrityError`
inside the atomic block and re-fetching the row that won the race.

DDD layering note
-----------------
This module is an **application service**. It deliberately crosses
bounded contexts to import the Django `Project` ORM model from
``platform_core.infrastructure.django.models``. Justification:

* `Project` is owned by the F8 / platform_core context, not by
  classification. Calling its persistence layer from classification is a
  cross-bounded-context call, which is explicitly allowed for
  *application* services (per the brief and the convention used by
  ingestion services that touch `ContractSubmission`).
* Domain code under ``classification.domain`` MUST NOT import this
  module — keep the dependency direction one-way.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction
from django.utils import timezone

from classification.domain.project_link import ProjectLinkResult

# Cross-bounded-context import: see module docstring "DDD layering note".
from platform_core.infrastructure.django.models import Project

if TYPE_CHECKING:
    from classification.domain.project_name_extraction import ProjectNameExtraction

logger = logging.getLogger(__name__)


_PLACEHOLDER_METADATA_FLAG: dict[str, bool] = {"placeholder": True}
"""`Project.metadata` payload set on placeholder rows so PRD_F8 US-09's
recompute job can exclude them from global aggregates."""


class ProjectLinker:
    """Resolve a `ProjectNameExtraction` into a `Project` row.

    Stateless: holds no per-call state. Safe to instantiate once per worker
    and reuse. Provided as a class (rather than a free function) for
    consistency with the other classification application services and so
    future dependencies (clock, audit logger) can be injected without
    breaking callers.
    """

    def link_or_create_project(self, extraction: ProjectNameExtraction) -> ProjectLinkResult:
        """Link the extraction to a `Project` row, creating one when needed.

        Behaviour split (see module docstring for the full policy):

        * Placeholder input → always INSERT, never dedupe.
        * Real-name input → SELECT by ``normalized_name``; INSERT on miss,
          refresh ``last_analyzed`` on hit.

        Wrapped in ``transaction.atomic()`` so the SELECT-then-INSERT path
        cannot race with a concurrent INSERT — `IntegrityError` from the
        unique constraint triggers a re-fetch, returning the winner.

        Returns:
            A :class:`ProjectLinkResult` describing the row touched.
        """
        if extraction.is_placeholder:
            return self._create_placeholder(extraction)
        return self._upsert_named(extraction)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _create_placeholder(extraction: ProjectNameExtraction) -> ProjectLinkResult:
        """Always-insert path for placeholder names (PRD_F8 BR-07).

        `normalized_name` carries the deterministic ``unknown_<short_hash>``
        produced by `ProjectNameExtractor` and is unique by construction
        (different submissions hash differently). The `unique=True`
        constraint on `Project.normalized_name` will still surface a
        retry-safe error if two callers race on the *same* placeholder —
        in that case the first writer wins and we return its row.
        """
        canonical = extraction.raw or extraction.normalized
        with transaction.atomic():
            try:
                project = Project.objects.create(
                    canonical_name=canonical,
                    normalized_name=extraction.normalized,
                    last_analyzed=timezone.now(),
                    metadata=dict(_PLACEHOLDER_METADATA_FLAG),
                )
                return ProjectLinkResult(
                    project_id=project.id,
                    normalized_name=project.normalized_name,
                    was_created=True,
                    was_collision=False,
                )
            except IntegrityError:
                # Two workers raced on the same placeholder (same submission,
                # concurrent retries). Re-fetch and return the winner — still
                # "was_created" semantics from the caller's POV (the row
                # exists for this submission), but `was_collision=False`
                # because placeholders are not a dedupe path.
                logger.info(
                    "project_linker.placeholder_race_resolved",
                    extra={"normalized_name": extraction.normalized},
                )
                project = Project.objects.get(normalized_name=extraction.normalized)
                return ProjectLinkResult(
                    project_id=project.id,
                    normalized_name=project.normalized_name,
                    was_created=False,
                    was_collision=False,
                )

    @staticmethod
    def _upsert_named(extraction: ProjectNameExtraction) -> ProjectLinkResult:
        """SELECT-by-normalized-name, INSERT-on-miss path (PRD_F8 US-02)."""
        canonical = extraction.raw or extraction.normalized
        now = timezone.now()

        with transaction.atomic():
            existing = Project.objects.select_for_update().filter(normalized_name=extraction.normalized).first()
            if existing is not None:
                existing.last_analyzed = now
                existing.save(update_fields=["last_analyzed", "updated_at"])
                return ProjectLinkResult(
                    project_id=existing.id,
                    normalized_name=existing.normalized_name,
                    was_created=False,
                    was_collision=True,
                )

            try:
                project = Project.objects.create(
                    canonical_name=canonical,
                    normalized_name=extraction.normalized,
                    last_analyzed=now,
                )
                return ProjectLinkResult(
                    project_id=project.id,
                    normalized_name=project.normalized_name,
                    was_created=True,
                    was_collision=False,
                )
            except IntegrityError:
                # Concurrent insert won the race — fetch and treat as collision.
                logger.info(
                    "project_linker.upsert_race_resolved",
                    extra={"normalized_name": extraction.normalized},
                )
                project = Project.objects.get(normalized_name=extraction.normalized)
                project.last_analyzed = now
                project.save(update_fields=["last_analyzed", "updated_at"])
                return ProjectLinkResult(
                    project_id=project.id,
                    normalized_name=project.normalized_name,
                    was_created=False,
                    was_collision=True,
                )


__all__ = ["ProjectLinker"]
