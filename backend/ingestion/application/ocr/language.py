"""Language gate for extracted text (CS-056).

We accept Spanish (`es`). Anything else (or undetectable) is mapped to a
`NotAnalyzableError` so the API surfaces a stable rejection envelope.
"""

from __future__ import annotations

from ingestion.application.ocr.errors import NotAnalyzableError, NotAnalyzableReason

# Minimum number of characters before `langdetect` is asked to vote. Under
# this length, results are noise — treat as undetectable.
_MIN_CHARS_FOR_DETECTION = 20


def detect_language(text: str) -> str:
    """Return ISO 639-1 code. Raises `NotAnalyzableError` if not detectable."""

    cleaned = (text or "").strip()
    if len(cleaned) < _MIN_CHARS_FOR_DETECTION:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LANGUAGE_UNDETECTABLE,
            message=f"text shorter than {_MIN_CHARS_FOR_DETECTION} chars",
        )

    try:
        # Lazy import: keeps Django startup quick when ingestion isn't used.
        from langdetect import DetectorFactory, detect, lang_detect_exception  # noqa: PLC0415

        DetectorFactory.seed = 0  # deterministic
        return detect(cleaned)
    except lang_detect_exception.LangDetectException as exc:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LANGUAGE_UNDETECTABLE,
            message=str(exc),
        ) from exc


def ensure_spanish(text: str) -> str:
    """Detect language; raise unless Spanish. Returns the detected code."""

    code = detect_language(text)
    if code != "es":
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.REJECTED_LANGUAGE,
            message=f"detected {code!r}, expected 'es'",
        )
    return code
