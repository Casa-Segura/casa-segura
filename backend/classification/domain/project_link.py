"""Project linkage result DTO (CS-112).

PRD references:
    - PRD_F2_CLASIFICACION US-02: extracted project name resolves to a
      `Project.id` that gets attached to `ContractAnalysis.project_id`
      before downstream queues fire.
    - PRD_F8_PERSISTENCIA_PROYECTO_RETENCION US-02 + BR-07: upsert by
      `normalized_name`; placeholder rows are NEVER deduped.

DDD note: domain layer; no Django / infra imports. The `project_id` is
typed as `uuid.UUID` because `Project.id` is a `UUIDField`. The
application-layer `ProjectLinker` produces these from the ORM result.
"""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class ProjectLinkResult(BaseModel):
    """Outcome of `ProjectLinker.link_or_create_project`.

    Fields:
        project_id: UUID of the linked `Project` row (always populated —
            the linker either created or upserted, never returns `None`).
        normalized_name: the slug actually persisted on the row. Echoed
            here so callers can log it without re-querying.
        was_created: True when a fresh `Project` row was INSERTed (either
            because the normalized name was new or because the input was
            a placeholder, which always creates).
        was_collision: True when the linker found an existing row by
            `normalized_name` (dedupe path). Mutually exclusive with
            `was_created`. For placeholders this is always False per
            PRD_F8 BR-07.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: uuid.UUID = Field(description="UUID of the linked Project row.")
    normalized_name: str = Field(
        min_length=1,
        max_length=255,
        description="The slug stored on `Project.normalized_name` for this row.",
    )
    was_created: bool = Field(
        description="True if the linker INSERTed a fresh row (new normalized_name OR placeholder).",
    )
    was_collision: bool = Field(
        description=(
            "True if an existing Project was found by `normalized_name` (dedupe hit). "
            "Always False for placeholder inputs (PRD_F8 BR-07)."
        ),
    )


__all__ = ["ProjectLinkResult"]
