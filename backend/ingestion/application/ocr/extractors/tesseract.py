"""Tesseract Spanish fallback (CS-055).

Used when:
  * `OCR_TESSERACT_ENABLED` is true, and
  * either the Pixtral path failed N times or the router selected
    `TESSERACT` directly for an unknown-MIME image.

Requires the system `tesseract` binary and the Spanish trained data
(`spa.traineddata`). If either is missing, raises
`NotAnalyzableError(OCR_UNAVAILABLE)` so the upper layers can record a
clean error code without bringing down the worker.
"""

from __future__ import annotations

from io import BytesIO

import structlog

from django.conf import settings

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.ocr.language import ensure_spanish
from ingestion.application.ocr.tokens import count_tokens

logger = structlog.get_logger(__name__)


def extract_via_tesseract(*, file_bytes: bytes, content_type: str) -> ExtractionResult:
    """Run Tesseract on a single image. PDFs are not handled here —
    if the router lands on Tesseract for a PDF the orchestrator should
    short-circuit to `OCR_UNAVAILABLE` instead of rasterising in worker.
    """

    if not settings.OCR_TESSERACT_ENABLED:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.OCR_UNAVAILABLE,
            message="tesseract disabled via OCR_TESSERACT_ENABLED",
        )

    if not file_bytes:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.EMPTY_FILE,
            message="empty file buffer",
        )

    try:
        # Lazy: pytesseract/PIL only needed when the fallback path actually runs.
        import pytesseract  # type: ignore[import-not-found]  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.OCR_UNAVAILABLE,
            message=f"pytesseract/PIL missing: {exc}",
        ) from exc

    try:
        image = Image.open(BytesIO(file_bytes))
    except Exception as exc:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.CORRUPT_FILE,
            message=f"cannot open image: {exc}",
        ) from exc

    lang = settings.OCR_TESSERACT_LANG
    min_confidence = settings.OCR_TESSERACT_MIN_CONFIDENCE

    try:
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            output_type=pytesseract.Output.DICT,
        )
    except pytesseract.TesseractNotFoundError as exc:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.OCR_UNAVAILABLE,
            message=f"tesseract binary missing: {exc}",
        ) from exc
    except pytesseract.TesseractError as exc:
        message = str(exc)
        if "language" in message.lower() or "traineddata" in message.lower():
            raise NotAnalyzableError(
                reason=NotAnalyzableReason.OCR_UNAVAILABLE,
                message=f"tesseract language data missing ({lang}): {message}",
            ) from exc
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LOW_CONFIDENCE_OCR,
            message=message,
        ) from exc

    words = data.get("text", []) or []
    confs = data.get("conf", []) or []
    accepted = [
        word for word, conf in zip(words, confs, strict=False) if word.strip() and _safe_float(conf) >= min_confidence
    ]
    text = " ".join(accepted).strip()

    if not text:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LOW_CONFIDENCE_OCR,
            message=f"tesseract produced no words above confidence {min_confidence}",
        )

    language = ensure_spanish(text)
    return ExtractionResult(
        text=text,
        token_count=count_tokens(text),
        language=language,
        page_count=None,
    )


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0
