"""`ocr.detect_kind` routing (CS-052).

Given a file's MIME type + raw bytes, decide which extractor to try first:

  * Native-text PDF  → `pypdf`   (CS-053)
  * Scanned PDF      → `pixtral` (CS-054) — Pixtral handles PDFs natively
                       via the OpenRouter `file-parser` plugin.
  * Image            → `pixtral` (CS-054) — image_url block, no plugin.
  * Anything else    → `tesseract` fallback if it's an image, else reject.

The router does not call the extractors; it only returns the strategy
enum + a brief reason so the orchestrator can log/fan out attempts.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

import structlog

from ingestion.domain.enums import ExtractionStrategy, FileFormat

logger = structlog.get_logger(__name__)

# Minimum chars of extractable text per PDF for it to count as "native text"
# instead of a scanned image. Tuned conservatively: small contracts often
# have a few hundred chars per page.
_PDF_NATIVE_TEXT_THRESHOLD = 200


PDF_MIME = "application/pdf"
IMAGE_MIMES: frozenset[str] = frozenset({"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"})


@dataclass(frozen=True)
class RoutingDecision:
    strategy: ExtractionStrategy
    reason: str
    file_format: FileFormat


def detect_kind(*, content_type: str, file_bytes: bytes, filename: str = "") -> RoutingDecision:
    """Pick the initial extraction strategy for a freshly received file.

    Routing precedence (most specific → least):
      1. Trusted MIME or extension says "PDF" → pypdf if it carries native
         text, otherwise Pixtral (with the file-parser plugin).
      2. Trusted MIME or extension says "image/<jpeg|png|webp|heic>" →
         Pixtral with an `image_url` block.
      3. Nothing trusted → fall back to Tesseract OCR. Pixtral is *not*
         invoked for unknown inputs to avoid burning OpenRouter credits
         on garbage bytes; Tesseract will return `OCR_UNAVAILABLE` if the
         binary or `spa.traineddata` is missing, which the orchestrator
         turns into a clean `not_analyzable` envelope.
    """

    content_type = (content_type or "").lower()
    fmt = _detect_file_format(content_type=content_type, filename=filename)

    trusted_pdf = content_type == PDF_MIME or (fmt == FileFormat.PDF and filename.lower().endswith(".pdf"))
    trusted_image = content_type in IMAGE_MIMES or (
        fmt in {FileFormat.JPG, FileFormat.JPEG, FileFormat.PNG, FileFormat.WEBP, FileFormat.HEIC} and "." in filename
    )

    if trusted_pdf:
        if _pdf_has_native_text(file_bytes):
            return RoutingDecision(
                strategy=ExtractionStrategy.PYPDF,
                reason="pdf_with_extractable_text",
                file_format=FileFormat.PDF,
            )
        return RoutingDecision(
            strategy=ExtractionStrategy.VISION_LLM,
            reason="scanned_pdf_routed_to_pixtral",
            file_format=FileFormat.PDF,
        )

    if trusted_image:
        return RoutingDecision(
            strategy=ExtractionStrategy.VISION_LLM,
            reason="image_routed_to_pixtral",
            file_format=fmt,
        )

    # Fully unknown: try Tesseract as a last-resort offline fallback.
    return RoutingDecision(
        strategy=ExtractionStrategy.TESSERACT,
        reason="unknown_mime_fallback",
        file_format=fmt,
    )


def _detect_file_format(*, content_type: str, filename: str) -> FileFormat:
    """Map MIME → FileFormat, falling back to the filename extension."""

    mime_to_format = {
        PDF_MIME: FileFormat.PDF,
        "image/jpeg": FileFormat.JPEG,
        "image/jpg": FileFormat.JPG,
        "image/png": FileFormat.PNG,
        "image/webp": FileFormat.WEBP,
        "image/heic": FileFormat.HEIC,
    }
    if content_type in mime_to_format:
        return mime_to_format[content_type]

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    for fmt in FileFormat:
        if fmt.value == ext:
            return fmt
    return FileFormat.PDF  # safest default — pypdf will reject if not a PDF


def _pdf_has_native_text(file_bytes: bytes) -> bool:
    """Cheap probe: ask pypdf for the first page's text. If we get
    enough chars, treat the PDF as native-text and route to pypdf."""

    try:
        # Lazy import keeps Django startup quick; the probe runs only during
        # ingestion and most processes (frontend-facing API) never call it.
        from pypdf import PdfReader  # noqa: PLC0415

        reader = PdfReader(BytesIO(file_bytes))
        if not reader.pages:
            return False
        first_text = reader.pages[0].extract_text() or ""
        return len(first_text.strip()) >= _PDF_NATIVE_TEXT_THRESHOLD
    except Exception as exc:
        logger.info("ocr.router.pdf_probe_failed", error=str(exc))
        return False
