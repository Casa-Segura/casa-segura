"""`IndicatorsFound` DTO — free-text justifications surfaced by §8.1 (PRD_F2 §5.1).

PRD references:
    - PRD_F2_CLASIFICACION §8.1: classifier response key `indicators_found`
      (list of short Spanish strings explaining what the LLM relied on).
    - PRD_F2_CLASIFICACION §US-02 / BR-07: justifications must be free of
      PII surface; the report (EPIC-07) renders them verbatim, so length
      and shape constraints are enforced here.

Design notes:
    - Closed wrapper around `list[str]`. Enforces length caps (max 20
      indicators, each up to 240 chars) so a malformed LLM response cannot
      explode persisted JSONB. Pydantic v2 `extra="forbid"` keeps callers
      honest.
    - Frozen so downstream code passes it by reference without copy.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_INDICATORS: int = 20
MAX_INDICATOR_LENGTH: int = 240


class IndicatorsFound(BaseModel):
    """List of short Spanish justifications backing a classifier decision.

    Each entry is a single phrase (e.g. ``"compraventa con saldo a plazos"``)
    cited by the §8.1 prompt. The list is empty when the LLM did not surface
    indicators; downstream consumers must not treat absence as failure.

    Accepts both shapes at construction time:

        * ``IndicatorsFound(items=("a", "b"))``                — programmatic
        * ``IndicatorsFound.model_validate(["a", "b"])``       — LLM-shaped
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    items: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Short justifications surfaced by §8.1; tuple to keep the model hashable.",
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_bare_list(cls, value: Any) -> Any:
        """LLM returns `indicators_found: [...]`; map that bare list onto `items`."""
        if isinstance(value, (list, tuple)):
            return {"items": tuple(value)}
        return value

    @field_validator("items")
    @classmethod
    def _validate_items(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) > MAX_INDICATORS:
            raise ValueError(
                f"indicators_found must contain at most {MAX_INDICATORS} entries; got {len(value)}",
            )
        for entry in value:
            if not isinstance(entry, str):  # pydantic already validates, defensive
                raise ValueError(f"indicators_found entries must be str; got {type(entry).__name__}")
            stripped = entry.strip()
            if not stripped:
                raise ValueError("indicators_found entries must not be empty / whitespace-only")
            if len(stripped) > MAX_INDICATOR_LENGTH:
                raise ValueError(
                    f"indicators_found entry exceeds {MAX_INDICATOR_LENGTH} chars: {entry[:40]!r}…",
                )
        return value

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):  # type: ignore[override]
        return iter(self.items)


__all__ = ["MAX_INDICATORS", "MAX_INDICATOR_LENGTH", "IndicatorsFound"]
