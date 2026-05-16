"""Token counting for audit (CS-053, CS-057).

We count tokens with `tiktoken` (cl100k_base) so the number stored in
`ContractSubmission.extracted_text_token_count` is comparable across
ingestion strategies. The text itself is never persisted — only the count.
"""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


def count_tokens(text: str) -> int:
    """Return the number of tokens in `text`. Falls back to word count if
    `tiktoken` is unavailable so the pipeline still works in stripped envs."""

    if not text:
        return 0
    try:
        # Lazy: tiktoken adds ~30 MB on import and is only needed once we have text.
        import tiktoken  # noqa: PLC0415

        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception as exc:  # pragma: no cover — fallback when tiktoken/encoding is unavailable
        logger.warning("ocr.tokens.tiktoken_unavailable", error=str(exc))
        return len(text.split())
