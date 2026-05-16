"""Confidence model for classification and per-field extraction outputs.

PRD references:
    - PRD_F2_CLASIFICACION US-01: classification `confidence` thresholds
      that drive the orchestrator's accept / re-validate / reject decisions.
    - PRD_F2_CLASIFICACION US-04: per-field extraction `confidence` ∈ [0, 1]
      used by F5 (`PRD_F5 §US-01`) which treats `confidence < 0.5` as
      `not_present` downstream.
    - CS-114 AC: "`confidence` fields coerce/clamp or reject out-of-range
      values deterministically".

Threshold policy (single source of truth for downstream layers):
    - score ≥ 0.85  -> ConfidenceLevel.HIGH
        Classifier output accepted as-is (PRD_F2 §US-01).
    - 0.65 ≤ score < 0.85 -> ConfidenceLevel.MEDIUM
        Classifier output re-validated with the §8.3 prompt before accept.
    - score < 0.65 -> ConfidenceLevel.LOW
        Classification rejected → `NOT_CLASSIFIABLE` (PRD_F2 §US-06).

    Per-field extraction (`ExtractedFields`) uses the same `ConfidenceBand`
    container. F5's `not_present` cutoff (0.5) is *not* baked into the
    `ConfidenceLevel` mapping above — F5 consumes the raw `score`
    directly via `ConfidenceBand.is_not_present_for_economics()`.

Validation policy (CS-114 BVA):
    - Scores outside [0.0, 1.0] are *rejected* (raise ValidationError).
      Coercion would silently mask LLM bugs; rejection makes them visible
      and triggers the §8.3 re-validation path. The thresholds are exposed
      as module constants so downstream code never re-implements them.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Threshold constants — keep aligned with PRD_F2 §US-01 and CS-114 BVA table.
CONFIDENCE_HIGH_THRESHOLD: float = 0.85
CONFIDENCE_MEDIUM_THRESHOLD: float = 0.65
# F5 cutoff: per-field extraction scores below this are treated as `not_present`
# downstream (PRD_F5 US-01). Exposed as a constant so callers stop re-implementing
# the threshold ad hoc (CS-114 AC).
ECONOMICS_NOT_PRESENT_CUTOFF: float = 0.5


class ConfidenceLevel(StrEnum):
    """Discrete confidence bucket derived from a continuous score.

    The mapping from continuous score to discrete level is defined by
    `ConfidenceBand.level_from_score`. Downstream consumers (orchestrator,
    rubric, economics) MUST use that helper rather than re-implementing
    the thresholds.
    """

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConfidenceBand(BaseModel):
    """Score + discrete level + optional rationale.

    Used both for the global classification confidence and as the container
    inside `ContractExtraction.field_confidences` for per-field scores.

    Fields:
        level: discrete bucket (HIGH/MEDIUM/LOW); must be consistent with
            `score` per the thresholds documented in the module docstring.
        score: raw float in [0.0, 1.0]. Out-of-range values are rejected.
        rationale: optional short Spanish explanation for human-readable
            audit. MUST NOT contain PII (BR-07).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    level: ConfidenceLevel
    score: float = Field(ge=0.0, le=1.0)
    rationale: str | None = Field(default=None, max_length=500)

    @field_validator("score")
    @classmethod
    def _validate_score_range(cls, value: float) -> float:
        # Pydantic v2 already enforces ge/le via Field; this validator exists to
        # surface a clearer error path for non-numeric inputs that slip through
        # JSON deserialization (e.g. None coerced from missing keys).
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"confidence score must be in [0.0, 1.0]; got {value!r}")
        return value

    @classmethod
    def level_from_score(cls, score: float) -> ConfidenceLevel:
        """Map a raw score to its `ConfidenceLevel` per PRD_F2 thresholds.

        Thresholds (single source of truth):
            score ≥ 0.85 → HIGH
            score ≥ 0.65 → MEDIUM
            else         → LOW
        """
        if score >= CONFIDENCE_HIGH_THRESHOLD:
            return ConfidenceLevel.HIGH
        if score >= CONFIDENCE_MEDIUM_THRESHOLD:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    @classmethod
    def from_score(cls, score: float, rationale: str | None = None) -> ConfidenceBand:
        """Construct a band, deriving `level` from `score` via the canonical map.

        Convenience builder so producers never have to set `level` manually.
        """
        return cls(level=cls.level_from_score(score), score=score, rationale=rationale)

    def is_not_present_for_economics(self) -> bool:
        """Return True if this score must be treated as `not_present` by F5.

        Encapsulates PRD_F5 US-01's `confidence < 0.5` rule so consumers do
        not re-implement the threshold (CS-114 AC).
        """
        return self.score < ECONOMICS_NOT_PRESENT_CUTOFF


__all__ = [
    "CONFIDENCE_HIGH_THRESHOLD",
    "CONFIDENCE_MEDIUM_THRESHOLD",
    "ECONOMICS_NOT_PRESENT_CUTOFF",
    "ConfidenceBand",
    "ConfidenceLevel",
]
