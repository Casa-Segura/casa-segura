"""Project name extraction DTO (CS-112).

PRD references:
    - PRD_F2_CLASIFICACION US-02 §8.1: the LLM emits `project_name_canonical`
      (verbatim text) which is then normalized for matching.
    - PRD_F2_CLASIFICACION BR-05 / BR-06: normalization is the dedupe key;
      placeholder `unknown_<short_hash>` is used when extraction yields nothing
      meaningful.
    - PRD_F8_PERSISTENCIA_PROYECTO_RETENCION US-02 + BR-07: placeholder rows
      are NEVER deduped — each unextractable submission gets its own Project.
    - ADR-0003: the normalization algorithm strips generic words from both
      ends (`residencial`, `proyecto`, ...), so two ostensibly different
      raw strings can collide to the same `normalized` value — that is the
      intended dedupe path.

DDD note: this lives in `classification.domain`, so it MUST NOT import
infrastructure (Django, httpx). It imports the pure normalization helpers
from `platform_core.domain` per ADR-0002's cross-bounded-context
allowance for shared *domain* code (no Django involvement).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from platform_core.domain.project_name import is_placeholder_normalized_name


class ProjectNameExtraction(BaseModel):
    """Result of the project-name extraction step (CS-112).

    Fields:
        raw: the verbatim text the LLM reported as the project name. `None`
            when extraction returned nothing (the placeholder path applies).
        normalized: the slug produced by `normalize_project_name`. Always a
            non-empty string — when the LLM returned nothing or the
            normalized form was too short, callers populate this with the
            `unknown_<short_hash>` placeholder produced by
            `ProjectNameExtractor`.
        is_placeholder: derived flag set by the post-init validator using
            `is_placeholder_normalized_name`. Downstream `ProjectLinker`
            uses this to bypass dedupe per PRD_F8 BR-07.
        confidence: model self-reported extraction confidence in [0.0, 1.0].
            Surfaced for observability only; CS-112 does not gate behaviour
            on this value (the placeholder path is driven by `normalized`
            length, not confidence).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    raw: str | None = Field(
        default=None,
        max_length=255,
        description="Verbatim project-name string from the LLM (PRD_F2 US-02 `canonical_name`).",
    )
    normalized: str = Field(
        min_length=1,
        max_length=255,
        description=(
            "Normalized slug used as the Project dedupe key. Always populated; "
            "callers map empty/insufficient input to `unknown_<short_hash>` "
            "BEFORE constructing this DTO."
        ),
    )
    is_placeholder: bool = Field(
        default=False,
        description="True when `normalized` matches the `unknown_<hex>` pattern (PRD_F8 BR-07).",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="LLM self-reported confidence in the extraction (0.0-1.0).",
    )

    @model_validator(mode="after")
    def _derive_placeholder_flag(self) -> ProjectNameExtraction:
        """Force `is_placeholder` to match `normalized` shape — never trust the caller.

        Pydantic's `frozen=True` forbids direct attribute assignment after
        construction, so we go through ``object.__setattr__`` to enforce the
        invariant. This mirrors the pattern used by other frozen DTOs that
        need a derived field (e.g. `ConfidenceBand`).
        """
        expected = is_placeholder_normalized_name(self.normalized)
        if self.is_placeholder != expected:
            object.__setattr__(self, "is_placeholder", expected)
        return self


__all__ = ["ProjectNameExtraction"]
