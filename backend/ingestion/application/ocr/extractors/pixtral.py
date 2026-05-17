"""Pixtral Large 2411 extractor via OpenRouter (CS-054).

Routing summary:

  * Images (`image/jpeg`, `image/png`, `image/webp`, …) → single chat
    completion with a `image_url` content block containing the base64
    data URL. No plugins.

  * PDFs (`application/pdf`) → single chat completion with a `file`
    content block (filename + base64 file_data) AND a root-level
    `plugins=[{"id": "file-parser", "pdf": {"engine": "mistral-ocr"}}]`
    so OpenRouter pre-parses the PDF with Mistral OCR before sending
    text to Pixtral.

The same Pixtral model handles both — no separate slugs needed.
"""

from __future__ import annotations

import base64

import structlog

from django.conf import settings

from ingestion.application.ocr.errors import (
    ExtractionResult,
    NotAnalyzableError,
    NotAnalyzableReason,
)
from ingestion.application.ocr.language import ensure_spanish
from ingestion.application.ocr.metrics import OPENROUTER_CALLS
from ingestion.application.ocr.tokens import count_tokens
from shared.llm.openrouter import OpenRouterClient, OpenRouterError

logger = structlog.get_logger(__name__)

DEFAULT_PROMPT = (
    "Extrae todo el texto legible de este documento. Devuelve el texto "
    "íntegro, manteniendo el orden original. Si hay tablas, transcríbelas "
    "en formato markdown. No agregues comentarios."
)

PDF_MIME = "application/pdf"
IMAGE_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
}


def extract_via_pixtral(
    *,
    file_bytes: bytes,
    content_type: str,
    filename: str,
    prompt: str = DEFAULT_PROMPT,
    client: OpenRouterClient | None = None,
) -> ExtractionResult:
    """Run Pixtral Large 2411 against an image or a PDF.

    `client` may be injected for testing; defaults to a fresh client built
    from Django settings.
    """

    if not file_bytes:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.EMPTY_FILE,
            message="empty file buffer",
        )

    payload_messages, plugins = _build_payload(
        file_bytes=file_bytes,
        content_type=content_type,
        filename=filename,
        prompt=prompt,
    )

    own_client = client is None
    client = client or OpenRouterClient()
    model = settings.OPENROUTER_OCR_MODEL
    try:
        try:
            result = client.chat_completion(
                model=model,
                messages=payload_messages,
                plugins=plugins,
            )
        except OpenRouterError as exc:
            OPENROUTER_CALLS.labels(model=model, outcome="error").inc()
            logger.warning(
                "ocr.pixtral.openrouter_error",
                status_code=exc.status_code,
                model=model,
            )
            raise NotAnalyzableError(
                reason=NotAnalyzableReason.UPSTREAM_LLM_ERROR,
                message=str(exc),
            ) from exc
    finally:
        if own_client:
            client.close()

    OPENROUTER_CALLS.labels(model=model, outcome="success").inc()

    text = (result.content or "").strip()
    if not text:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.LOW_CONFIDENCE_OCR,
            message="pixtral returned empty content",
        )

    language = ensure_spanish(text)

    return ExtractionResult(
        text=text,
        token_count=count_tokens(text),
        language=language,
        page_count=None,
        tokens_consumed=(result.tokens_prompt or 0) + (result.tokens_completion or 0) or None,
        cost_estimate_cents=result.cost_usd_cents,
    )


def _build_payload(
    *,
    file_bytes: bytes,
    content_type: str,
    filename: str,
    prompt: str,
) -> tuple[list[dict], list[dict] | None]:
    """Construct the `messages` array + optional `plugins` list."""

    mime = (content_type or "").lower()
    b64 = base64.b64encode(file_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"

    content: list[dict] = [{"type": "text", "text": prompt}]

    if mime in IMAGE_MIMES:
        content.append({"type": "image_url", "image_url": {"url": data_url}})
        plugins: list[dict] | None = None

    elif mime == PDF_MIME:
        content.append(
            {
                "type": "file",
                "file": {
                    "filename": filename or "contract.pdf",
                    "file_data": data_url,
                },
            }
        )
        plugins = [
            {
                "id": "file-parser",
                "pdf": {"engine": settings.OPENROUTER_PDF_PLUGIN_ENGINE},
            }
        ]

    else:
        raise NotAnalyzableError(
            reason=NotAnalyzableReason.UNSUPPORTED_FORMAT,
            message=f"unsupported mime type for pixtral: {mime!r}",
        )

    return [{"role": "user", "content": content}], plugins
