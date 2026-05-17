"""Text-PDF extraction with pypdf (CS-053).

Used when the router determines the PDF already has native text. Cheap,
deterministic, no LLM. The text never leaves this function — only
length/token-count metadata gets returned for downstream persistence.

PRD §US-05 requirements implemented here:

  * Concatenate pages with ``--- PAGE N ---`` separators (1-indexed) so
    downstream classification can attribute findings to specific pages.
  * Normalize whitespace + control chars: ``\\r\\n`` → ``\\n``, NBSP →
    space, soft-hyphen stripped, other C0/C1 control chars dropped while
    preserving newlines.
  * Enforce a **30s** wall-clock watchdog (``PYPDF_TIMEOUT_SECONDS``).
    The watchdog is granular per-page; large PDFs that stall on a single
    page surface ``NotAnalyzableReason.TIMEOUT`` instead of hanging the
    request thread. The orchestrator increments the
    ``INGEST_TIMEOUTS`` counter on this reason.
  * Surface ``LOW_CONFIDENCE_OCR`` when the normalized text is below the
    PRD-mandated 500-char floor. The orchestrator catches this and
    escalates to vision per PRD §US-05 BR-08.
"""

from __future__ import annotations

import re
import time
import unicodedata
from io import BytesIO

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.ocr.language import ensure_spanish
from ingestion.application.ocr.tokens import count_tokens


PYPDF_TIMEOUT_SECONDS = 30
PYPDF_MIN_CHARS = 500
PAGE_HEADER_TEMPLATE = "--- PAGE {n} ---"

# Match C0/C1 control characters EXCEPT line feed (\n) and tab (\t).
# Whitespace normalization is done separately.
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def extract_text_pdf(file_bytes: bytes) -> ExtractionResult:
    """Extract text from a native-text PDF.

    Raises ``NotAnalyzableError`` if the PDF is empty, corrupt, the
    30-second watchdog fires, the language gate rejects, or the
    normalized output is below the 500-char PRD floor.
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
    start = time.perf_counter()
    for index, page in enumerate(pages):
        if time.perf_counter() - start > PYPDF_TIMEOUT_SECONDS:
            raise NotAnalyzableError(
                reason=NotAnalyzableReason.TIMEOUT,
                message=(
                    f"pypdf wall-clock exceeded {PYPDF_TIMEOUT_SECONDS}s "
                    f"after page {index}/{len(pages)}"
                ),
            )
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""
        header = PAGE_HEADER_TEMPLATE.format(n=index + 1)
        parts.append(f"{header}\n\n{page_text}")

    full_text = _normalize_text("\n\n".join(parts))
    if not full_text:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LOW_CONFIDENCE_OCR,
            message="pypdf returned no text — likely scanned",
        )

    if len(full_text) < PYPDF_MIN_CHARS:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LOW_CONFIDENCE_OCR,
            message=(
                f"pypdf yielded {len(full_text)} chars < "
                f"{PYPDF_MIN_CHARS} (PRD §US-05 BR-08 minimum)"
            ),
        )

    language = ensure_spanish(full_text)

    return ExtractionResult(
        text=full_text,
        token_count=count_tokens(full_text),
        language=language,
        page_count=len(pages),
    )


def _normalize_text(text: str) -> str:
    """Whitespace + control-character normalization per PRD §US-05.

    Order matters: NFKC first so compatibility characters get folded
    into their canonical equivalents (e.g. fullwidth digits), then we
    flatten newlines, replace NBSP with regular spaces, strip
    soft-hyphens, and drop the remaining C0/C1 control bytes.
    """

    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    # \u00a0 = NBSP, \u00ad = soft hyphen, \u200b = zero-width space
    normalized = (
        normalized.replace("\u00a0", " ")
        .replace("\u00ad", "")
        .replace("\u200b", "")
    )
    normalized = _CONTROL_CHARS_RE.sub("", normalized)
    return normalized.strip()
