"""Text-PDF extraction with pypdf (CS-053).

Used when the router determines the PDF already has native text. Cheap,
deterministic, no LLM. The text never leaves this function — only
length/token-count metadata gets returned for downstream persistence.
"""

from __future__ import annotations

from io import BytesIO

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.ocr.language import ensure_spanish
from ingestion.application.ocr.tokens import count_tokens


def extract_text_pdf(file_bytes: bytes) -> ExtractionResult:
    """Extract text from a native-text PDF.

    Raises `NotAnalyzableError` if the PDF is empty, corrupt, or non-Spanish.
    """

    if not file_bytes:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.EMPTY_FILE,
            message="empty file buffer",
        )

    try:
        # Lazy: pypdf adds ~6 MB to Django startup but is only needed in the
        # text-PDF extraction path.
        from pypdf import PdfReader  # noqa: PLC0415

        reader = PdfReader(BytesIO(file_bytes))
    except Exception as exc:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.CORRUPT_FILE,
            message=f"pypdf failed to open: {exc}",
        ) from exc

    pages = reader.pages
    if not pages:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.CORRUPT_FILE,
            message="pdf has no pages",
        )

    parts: list[str] = []
    for page in pages:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text:
            parts.append(text)

    full_text = "\n\n".join(parts).strip()
    if not full_text:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LOW_CONFIDENCE_OCR,
            message="pypdf returned no text — likely scanned",
        )

    language = ensure_spanish(full_text)

    return ExtractionResult(
        text=full_text,
        token_count=count_tokens(full_text),
        language=language,
        page_count=len(pages),
    )
