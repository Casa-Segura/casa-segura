"""Language gate for extracted text (CS-056).

PRD §US-08 / BR-09:

  * Evaluate language detection on the **first 2000 characters** of the
    normalized text. Anything past that is signal-thin and slows the
    detector for no quality gain.
  * Use ``langdetect.detect_langs`` (not ``detect``) so we have access to
    each candidate's probability.
  * Spanish (``es``) is the only accepted top language.
      - ``es`` with probability **> 0.85** → continue without warning.
      - ``es`` with probability **≤ 0.85** → continue with a structured
        ``ocr.language.low_confidence`` warning log (the OCR result still
        flows downstream, but observability can flag noisy detections).
      - any other top language → ``REJECTED_LANGUAGE``. The HTTP layer
        maps this to **422 LANGUAGE_NOT_SUPPORTED** per [[PRD_F1_INGESTA_Y_OCR]]
        §7.4.
"""

from __future__ import annotations

import structlog

from ingestion.application.ocr.errors import NotAnalyzableError, NotAnalyzableReason

logger = structlog.get_logger(__name__)

# Minimum number of characters before `langdetect` is asked to vote. Under
# this length, results are noise — treat as undetectable.
_MIN_CHARS_FOR_DETECTION = 20

# PRD §US-08 detection window — language gate looks at the first slice
# only so a long contract with a one-paragraph English boilerplate at the
# end still classifies as Spanish.
LANGUAGE_DETECTION_WINDOW_CHARS = 2000

# PRD §US-08 confidence comparator: strict `> 0.85` means 0.85 itself
# continues but with a low-confidence warning.
LANGUAGE_CONFIDENCE_THRESHOLD = 0.85


def detect_language(text: str) -> tuple[str, float]:
    """Return ``(iso_code, probability)`` for the top candidate.

    Probability is in ``[0.0, 1.0]`` per ``langdetect.detect_langs``.
    Raises ``NotAnalyzableError(LANGUAGE_UNDETECTABLE)`` when there isn't
    enough text or when ``langdetect`` raises.
    """

    cleaned = (text or "").strip()
    if len(cleaned) < _MIN_CHARS_FOR_DETECTION:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LANGUAGE_UNDETECTABLE,
            message=f"text shorter than {_MIN_CHARS_FOR_DETECTION} chars",
        )

    window = cleaned[:LANGUAGE_DETECTION_WINDOW_CHARS]

    try:
        # Lazy import: keeps Django startup quick when ingestion isn't used.
        from langdetect import DetectorFactory, detect_langs, lang_detect_exception  # noqa: PLC0415

        DetectorFactory.seed = 0  # deterministic
        candidates = detect_langs(window)
    except lang_detect_exception.LangDetectException as exc:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LANGUAGE_UNDETECTABLE,
            message=str(exc),
        ) from exc

    if not candidates:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LANGUAGE_UNDETECTABLE,
            message="langdetect returned no candidates",
        )

    top = candidates[0]
    return top.lang, float(top.prob)


def ensure_spanish(text: str) -> str:
    """Detect language; raise unless Spanish. Returns the detected code.

    When the top language is Spanish but its probability is at or below
    ``LANGUAGE_CONFIDENCE_THRESHOLD``, emits a structured warning log so
    the observability pipeline can flag noisy detections without blocking
    the submission (PRD §US-08 bullet 3 semantics).
    """

    code, prob = detect_language(text)
    if code != "es":
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.REJECTED_LANGUAGE,
            message=f"detected {code!r} (p={prob:.3f}), expected 'es'",
        )

    if prob <= LANGUAGE_CONFIDENCE_THRESHOLD:
        logger.warning(
            "ocr.language.low_confidence",
            detected=code,
            probability=round(prob, 4),
            threshold=LANGUAGE_CONFIDENCE_THRESHOLD,
        )
    return code
