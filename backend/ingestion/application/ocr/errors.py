"""Stable error envelope for the ingestion pipeline (CS-056).

Each failure carries an `error_code` that survives across versions so
clients (frontend, retry queues, provider callbacks) can branch on it without
parsing free-form messages. The codes are also persisted on
`ContractSubmission.error_code` / `OcrJob.error_code`.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class NotAnalyzableReason(StrEnum):
    """Why a submission could not be analysed.

    Values are persisted in `error_code`; keep them stable.
    """

    UNSUPPORTED_FORMAT = "unsupported_format"
    SIZE_EXCEEDED = "size_exceeded"
    PAGE_COUNT_EXCEEDED = "page_count_exceeded"
    EMPTY_FILE = "empty_file"
    CORRUPT_FILE = "corrupt_file"
    REJECTED_LANGUAGE = "rejected_language"
    LANGUAGE_UNDETECTABLE = "language_undetectable"
    LOW_CONFIDENCE_OCR = "low_confidence_ocr"
    OCR_UNAVAILABLE = "ocr_unavailable"
    UPSTREAM_LLM_ERROR = "upstream_llm_error"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class NotAnalyzableError(Exception):
    """Raised by extractors when a submission can't yield analysable text."""

    reason: NotAnalyzableReason
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.reason.value}: {self.message}"


@dataclass(frozen=True)
class ExtractionResult:
    """Successful extraction output. The text itself is in-memory only —
    callers MUST NOT persist it (see CS-057 invariant).
    """

    text: str
    token_count: int
    language: str | None
    page_count: int | None
    tokens_consumed: int | None = None
    cost_estimate_cents: int | None = None
