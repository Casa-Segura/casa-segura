"""Cross-encoder reranker for RAG retrieval (CS-087 follow-up).

The bi-encoder dense retrieval (`embed_query` + pgvector) gives us solid
recall (Top-5 article-level ≈ 0.80 on the eval set) but weak ordering:
the right answer often lands at rank 2-4 because cosine scores cluster
within ~0.03. This module wraps a cross-encoder (default
`BAAI/bge-reranker-v2-m3`, multilingual, 568M params) that scores each
(query, candidate) pair attending to both sequences and produces a
much more discriminative relevance score.

Flow: bi-encoder pulls top-N (RAG_RERANKER_POOL_SIZE) for recall;
this module reorders by cross-encoder score; caller keeps top-K.
"""

from __future__ import annotations

from threading import Lock

import structlog
from django.conf import settings

logger = structlog.get_logger(__name__)

_model = None
_model_lock = Lock()


def is_enabled() -> bool:
    return bool(getattr(settings, "RAG_RERANKER_ENABLED", False))


def get_reranker_model():
    """Return the lazily-loaded cross-encoder singleton."""

    global _model  # noqa: PLW0603 — process-wide singleton, guarded by _model_lock
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            from sentence_transformers import CrossEncoder  # noqa: PLC0415

            logger.info(
                "reranker.loading_model",
                model=settings.RAG_RERANKER_MODEL,
                device=settings.EMBEDDING_DEVICE,
            )
            _model = CrossEncoder(
                settings.RAG_RERANKER_MODEL,
                device=settings.EMBEDDING_DEVICE,
            )
    return _model


def score(query: str, passages: list[str]) -> list[float]:
    """Return one rerank score per passage, in input order.

    Higher = more relevant. Scale is model-specific (bge-reranker emits
    raw logits; sigmoid for [0,1] if needed).
    """

    if not passages:
        return []
    model = get_reranker_model()
    pairs = [[query, p] for p in passages]
    scores = model.predict(pairs, show_progress_bar=False)
    return [float(s) for s in scores]
