"""Embedding pipeline (CS-083).

Wraps `sentence-transformers` so the corpus ingestion CLI (CS-084) and
the retrieval service (CS-085) can both produce vectors with consistent
shape (1024 dims, `intfloat/multilingual-e5-large` by default).

The e5 family requires input prefixes for retrieval to work correctly:
`passage: ` for documents being indexed and `query: ` for the question
being asked. Missing prefixes drops same-language similarity by
~0.10-0.15 in our internal sweep, which is why both `embed_texts` and
`embed_query` apply the prefix automatically.

The model is loaded once per process and cached on the module --- Django
worker boots are cheap (~1-2s for the first encode), and idle memory is
~1.2 GB.
"""

from __future__ import annotations

from collections.abc import Iterable
from threading import Lock

import structlog

from django.conf import settings

logger = structlog.get_logger(__name__)

EMBEDDING_DIM = 1024

_PASSAGE_PREFIX = "passage: "
_QUERY_PREFIX = "query: "

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


def _encode(texts: list[str], *, batch_size: int) -> list[list[float]]:
    model = get_embedding_model()

    if hasattr(model, "max_seq_length"):
        max_len = int(model.max_seq_length)
        truncated = sum(1 for t in texts if len(t) > max_len * 4)
        if truncated:
            logger.info("embeddings.truncating", count=truncated, max_len=max_len)

    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return [v.tolist() for v in vectors]


def embed_texts(texts: Iterable[str], *, batch_size: int | None = None) -> list[list[float]]:
    """Return a list of 768-dim vectors for passages to be indexed.

    Each input is prefixed with `passage: ` per the e5 retrieval contract.
    Empty/whitespace inputs receive a deterministic zero vector so callers
    don't have to filter them upstream.
    """

    bs = batch_size or settings.EMBEDDING_BATCH_SIZE
    materialised = [t or "" for t in texts]
    if not materialised:
        return []

    prefixed = [f"{_PASSAGE_PREFIX}{t}" for t in materialised]
    return _encode(prefixed, batch_size=bs)


def embed_query(text: str) -> list[float]:
    """Embed a single query using the `query: ` prefix per e5 contract."""

    if not text or not text.strip():
        return [0.0] * EMBEDDING_DIM
    return _encode([f"{_QUERY_PREFIX}{text}"], batch_size=1)[0]
