"""Per-slot extraction status enum for aggregated economic payloads (CS-116).

PRD references:
    - PRD_F2_CLASIFICACION US-04: per-field `extraction_status` semantics
      ("present" / "not_present" / "ambiguous") that the §8.5 prompt
      surfaces to F5.
    - PRD_F5_ANALISIS_ECONOMICO US-01: rule "if `value` is `null` or
      `confidence < 0.5` → mark the field `not_present`".
    - PRD_F5_ANALISIS_ECONOMICO BR-09: F5 MUST NOT silently substitute
      zeros for missing fields. This enum is the typed counterpart of
      that honesty requirement — every economic slot is marked one of
      `PRESENT` / `NOT_PRESENT` / `AMBIGUOUS` / `INVALID` so the rubric
      engine and persistence layer (CS-137) never read "missing" as 0.
    - CS-114 (`confidence.ECONOMICS_NOT_PRESENT_CUTOFF = 0.5`): the
      single source of truth for the `NOT_PRESENT` confidence boundary.

Status semantics (canonical — keep aligned with CS-116 AC1):
    PRESENT       — value is set AND confidence >= 0.5 (F5 US-01 cutoff).
                    Downstream layers may treat the slot as a usable
                    economic figure for derivations and benchmark
                    comparisons.
    NOT_PRESENT   — value is `None` OR confidence < 0.5 (PRD F5 US-01).
                    The contract did not state the figure, or the
                    extractor's confidence is below the F5 cutoff. The
                    rubric must NOT substitute a zero (BR-09); the
                    `EconomicSummary` should mark the corresponding
                    derived field unverifiable.
    AMBIGUOUS     — the extractor signalled ambiguity (e.g. two
                    conflicting figures appear in the contract). The
                    numeric value (if any) is suppressed; downstream
                    consumers MUST treat the slot as unverifiable, not
                    pick one of the candidates.
    INVALID       — the LLM emitted a value that violated the
                    `ExtractedFields` validator (e.g. negative price,
                    out-of-range percentage) and was demoted to
                    unverifiable by CS-113's extractor. Distinct from
                    `NOT_PRESENT` so observability can isolate "LLM
                    returned nonsense" from "contract is silent".

DDD note:
    This module lives in `domain/` and therefore must NOT import
    infrastructure (Django, httpx, etc.). It depends only on the stdlib.
"""

from __future__ import annotations

from enum import StrEnum


class ExtractionStatus(StrEnum):
    """Closed set of per-slot extraction outcomes (CS-116 AC1)."""

    PRESENT = "present"
    """Value is set AND confidence >= ECONOMICS_NOT_PRESENT_CUTOFF (0.5)."""

    NOT_PRESENT = "not_present"
    """Value is `None` OR confidence < 0.5 (PRD F5 US-01)."""

    AMBIGUOUS = "ambiguous"
    """Extractor flagged conflicting candidates; numeric suppressed (PRD F2 US-04)."""

    INVALID = "invalid"
    """Value violated a CS-113 pydantic validator and was demoted (BR-09)."""


__all__ = ["ExtractionStatus"]
