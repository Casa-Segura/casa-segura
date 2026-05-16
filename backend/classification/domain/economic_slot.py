"""Single economic-field slot with status + value + confidence (CS-116).

PRD references:
    - PRD_F2_CLASIFICACION US-04: per-field `{value, confidence, extraction_status}`
      shape published to F5 in `economic_fields_raw`.
    - PRD_F5_ANALISIS_ECONOMICO US-01: `confidence < 0.5` ⇒ `not_present`.
    - PRD_F5_ANALISIS_ECONOMICO BR-09: no zero substitution for missing values.
    - DOMAIN_MODEL §5.5: each `EconomicSummary.fields_extracted` entry is
      a typed slot. `EconomicSlot` is the in-memory carrier that CS-137
      will project into that JSONB shape.

DDD note:
    Domain layer — pydantic v2 only, no Django / infra imports.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from classification.domain.extraction_status import ExtractionStatus


class EconomicSlot(BaseModel):
    """One economic field's full provenance for downstream consumption.

    Fields:
        field_name: attribute name on `ExtractedFields` (e.g. `purchase_price_usd`).
        status: closed-set `ExtractionStatus` — never silently zero (BR-09).
        value: the coerced extracted value (float / int / str) when the
            slot is `PRESENT`. For `NOT_PRESENT` / `AMBIGUOUS` / `INVALID`
            slots, `value` may still be populated for diagnostics (e.g.
            the rejected invalid value) but consumers MUST NOT use it for
            computation — they MUST gate on `status == PRESENT`.
        confidence: raw [0, 1] score from the extractor, when available.
            `None` means the LLM omitted the confidence; per PRD F5 US-01
            that is treated as `NOT_PRESENT`.
        rationale: optional short Spanish audit string (no PII per BR-04).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    field_name: str = Field(min_length=1, max_length=64)
    status: ExtractionStatus
    value: float | int | str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    rationale: str | None = Field(default=None, max_length=500)


__all__ = ["EconomicSlot"]
