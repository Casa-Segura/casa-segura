"""Application-layer errors for the F2 classification pipeline.

These are *application*-level exceptions: they wrap upstream infrastructure
failures (OpenRouter transport, JSON parse, schema violations) into a
stable type that orchestrators and Celery tasks can branch on without
catching ``RuntimeError`` (which would also swallow programming bugs).

The classification primary call (CS-110) already defines
``ClassificationError`` inline; this module hosts the sibling errors
shared by downstream stages so each stage owns one typed failure surface.

Each error carries an optional ``code`` aligned with the canonical F2
error codes documented in
``docs/analysis/F2_clasificacion/IMPLEMENTATION_PLAN.md`` ("Error Codes"
section): ``LLM_PARSE_FAILED``, ``LLM_TRANSIENT_FAILURE``, etc. Callers
map this code onto the persisted ``error_code`` column without parsing
the human-readable message.
"""

from __future__ import annotations


class EconomicExtractionError(RuntimeError):
    """Raised when economic field extraction (CS-113) cannot produce a result.

    Wraps:
        * OpenRouter transport / 5xx exhaustion (``LLM_TRANSIENT_FAILURE``).
        * JSON parse failures after fence-strip recovery (``LLM_PARSE_FAILED``).
        * Top-level shape violations (e.g. the LLM returned an array
          instead of an object) — surfaced as ``LLM_PARSE_FAILED``.

    NOT raised for per-field validation failures. Those are handled by
    :class:`~classification.application.economic_extractor.EconomicFieldExtractor`
    by demoting the offending field to ``unverifiable`` per PRD_F2 BR-07,
    so a single bad LLM number never poisons an otherwise usable
    extraction.
    """

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


__all__ = ["EconomicExtractionError"]
