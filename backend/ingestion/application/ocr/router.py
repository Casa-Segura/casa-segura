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

# PRD §US-04: a PDF whose first page yields >100 meaningful characters
# from pypdf is treated as native-text. ≤100 chars → scanned, routed to vision.
_PDF_NATIVE_TEXT_THRESHOLD = 100


PDF_MIME = "application/pdf"
IMAGE_MIMES: frozenset[str] = frozenset({"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"})


@dataclass(frozen=True)
class RoutingDecision:
    strategy: ExtractionStrategy
    reason: str
    file_format: FileFormat


def detect_kind(
    *,
    content_type: str,
    file_bytes: bytes,
    filename: str = "",
    force_strategy: ExtractionStrategy | None = None,
) -> RoutingDecision:
    """Pick the initial extraction strategy for a freshly received file.

    ``force_strategy`` is a QA-only override (PRD §7.1). When supplied, it
    bypasses automatic detection entirely; the override is auditable via the
    structured ``reason="forced_<strategy>"`` field so log readers can tell
    apart a forced run from an automatic one.
    """

    content_type = (content_type or "").lower()
    fmt = _detect_file_format(content_type=content_type, filename=filename)

    if force_strategy is not None:
        logger.info(
            "ocr.router.force_strategy",
            forced_strategy=force_strategy.value,
            file_format=fmt.value,
        )
        return RoutingDecision(
            strategy=force_strategy,
            reason=f"forced_{force_strategy.value}",
            file_format=fmt,
        )

    # Treat input as PDF only when MIME OR filename extension says so. The
    # `_detect_file_format` default of PDF is kept for the `file_format`
    # field but must not silently shove unknown MIMEs through the PDF probe.
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if content_type == PDF_MIME or ext == FileFormat.PDF.value:
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

    if content_type in IMAGE_MIMES or fmt in {
        FileFormat.JPG,
        FileFormat.JPEG,
        FileFormat.PNG,
        FileFormat.WEBP,
        FileFormat.HEIC,
    }:
        return RoutingDecision(
            strategy=ExtractionStrategy.VISION_LLM,
            reason="image_routed_to_pixtral",
            file_format=fmt,
        )

    # Default: try Tesseract as a last-resort offline fallback for anything
    # that smells like an image without a recognised MIME.
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
        # PRD §US-04 uses a strict `> 100` comparator: exactly 100 chars
        # still routes to vision; only 101+ qualifies as native-text PDF.
        return len(first_text.strip()) > _PDF_NATIVE_TEXT_THRESHOLD
    except Exception as exc:
        logger.info("ocr.router.pdf_probe_failed", error=str(exc))
        return False
