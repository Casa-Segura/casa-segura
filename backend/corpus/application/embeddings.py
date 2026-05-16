"""Embedding pipeline (CS-083).

Wraps `sentence-transformers` so the corpus ingestion CLI (CS-084) and
the retrieval service (CS-085) can both produce vectors with consistent
shape (384 dims, `paraphrase-multilingual-MiniLM-L12-v2` by default).

The model is loaded once per process and cached on the module — Django
worker boots are cheap (~1s for the first encode), and idle memory is
~200 MB.
"""

from __future__ import annotations

from threading import Lock
from collections.abc import Iterable

import structlog
from django.conf import settings

logger = structlog.get_logger(__name__)

EMBEDDING_DIM = 384

_model = None
_model_lock = Lock()


def get_embedding_model():
    """Return the lazily-loaded sentence-transformers model singleton."""

    global _model  # noqa: PLW0603 — process-wide singleton, guarded by _model_lock
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            # Lazy import: sentence-transformers + torch are >500 MB and only
            # needed when Phase-1 RAG actually runs.
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415

            logger.info(
                "embeddings.loading_model",
                model=settings.EMBEDDING_MODEL,
                device=settings.EMBEDDING_DEVICE,
            )
            _model = SentenceTransformer(
                settings.EMBEDDING_MODEL,
                device=settings.EMBEDDING_DEVICE,
            )
    return _model


def embed_texts(texts: Iterable[str], *, batch_size: int | None = None) -> list[list[float]]:
    """Return a list of 384-dim vectors, one per input text.

    Empty/whitespace inputs receive a deterministic zero vector so callers
    don't have to filter them upstream. Truncation events (input longer
    than the model's max_seq_len) are logged but not raised — the model
    truncates internally.
    """

    model = get_embedding_model()
    bs = batch_size or settings.EMBEDDING_BATCH_SIZE

    materialised = [t or "" for t in texts]
    if not materialised:
        return []

    if hasattr(model, "max_seq_length"):
        max_len = int(model.max_seq_length)
        truncated = sum(1 for t in materialised if len(t) > max_len * 4)
        if truncated:
            logger.info("embeddings.truncating", count=truncated, max_len=max_len)

    vectors = model.encode(
        materialised,
        batch_size=bs,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return [v.tolist() for v in vectors]


def embed_query(text: str) -> list[float]:
    """Convenience wrapper for a single query."""

    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM
    return embed_texts([text])[0]
