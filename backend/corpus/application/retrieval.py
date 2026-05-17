"""`LegalCitationService.retrieve_legal_basis` (CS-085 + CS-086 + CS-089).

Hybrid retrieval flow:

  1. Look at `PatternLegalLink` for the finding category. If any rows
     match, prefetch those chunks directly (CS-086).
  2. Otherwise, embed the finding text and run a pgvector cosine search
     against `LegalChunk.embedding`, filtered by the active corpus
     version (CS-085).
  3. Apply the `similarity >= threshold` cite-or-stay-silent rule.
  4. Always log the query into `rag_query_log` (CS-089) — without the
     raw text, only a SHA-256 hash.

Returns a list of `LegalCitation` dataclasses (chunk + score + source).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from datetime import timedelta

import structlog
from pgvector.django import CosineDistance

from django.conf import settings
from django.utils import timezone

from corpus.application.embeddings import embed_query
from corpus.application.reranker import is_enabled as reranker_enabled, score as reranker_score
from corpus.application.tags import normalize_tag
from corpus.application.version import latest_active
from corpus.infrastructure.django.models import (
    CorpusVersion,
    LegalChunk,
    PatternLegalLink,
    RagQueryLog,
)

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class LegalCitation:
    """One legal chunk that supports a finding, plus retrieval metadata."""

    chunk_id: str
    law_id: str
    article_number: str
    anchor: str
    text_paraphrased: str
    similarity: float
    source: str  # "pattern" | "vector"


class LegalCitationService:
    """Stateless retrieval facade. Reuses the embedding model singleton."""

    def __init__(self, *, corpus_version: CorpusVersion | None = None) -> None:
        self.corpus_version = corpus_version or latest_active()

    def retrieve_legal_basis(
        self,
        *,
        finding: str,
        finding_pattern: str | None = None,
        threshold: float | None = None,
        top_k: int | None = None,
    ) -> list[LegalCitation]:
        """Return legal citations supporting `finding`.

        `finding_pattern` (when provided) drives the CS-086 shortcut. If
        the pattern matches any rows, the result skips the vector search.
        Otherwise we embed `finding` and run cosine retrieval.
        """

        if not finding or not finding.strip():
            return []

        if self.corpus_version is None:
            logger.warning("rag.retrieve.no_active_corpus")
            return []

        threshold = threshold if threshold is not None else settings.RAG_SIMILARITY_THRESHOLD
        top_k = top_k if top_k is not None else settings.RAG_TOP_K

        started = time.perf_counter()
        citations, used_pattern = self._retrieve(
            finding=finding,
            finding_pattern=finding_pattern,
            threshold=threshold,
            top_k=top_k,
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        self._log_query(
            finding=finding,
            threshold=threshold,
            top_k=top_k,
            chunks_returned=len(citations),
            pattern_shortcut_used=used_pattern,
            latency_ms=elapsed_ms,
        )

        return citations

    # ─── internals ──────────────────────────────────────────────────────

    def _retrieve(
        self,
        *,
        finding: str,
        finding_pattern: str | None,
        threshold: float,
        top_k: int,
    ) -> tuple[list[LegalCitation], bool]:
        if finding_pattern:
            pattern_hits = self._pattern_lookup(finding_pattern, top_k=top_k)
            if pattern_hits:
                return pattern_hits, True

        vector_hits = self._vector_lookup(finding, threshold=threshold, top_k=top_k)
        return vector_hits, False

    def _pattern_lookup(self, finding_pattern: str, *, top_k: int) -> list[LegalCitation]:
        pattern_slug = normalize_tag(finding_pattern)
        if not pattern_slug:
            return []

        links = PatternLegalLink.objects.filter(finding_pattern=pattern_slug).order_by("-relevance")[:top_k]
        if not links:
            return []

        anchors = [(lk.law_id, lk.anchor) for lk in links]
        chunks_by_key: dict[tuple[str, str], LegalChunk] = {}
        for chunk in LegalChunk.objects.filter(
            corpus_version=self.corpus_version,
            law_id__in=[law for law, _ in anchors],
            anchor__in=[anchor for _, anchor in anchors],
        ):
            chunks_by_key[(chunk.law_id, chunk.anchor)] = chunk

        citations: list[LegalCitation] = []
        for link in links:
            chunk = chunks_by_key.get((link.law_id, link.anchor))
            if chunk is None:
                continue
            citations.append(
                LegalCitation(
                    chunk_id=str(chunk.id),
                    law_id=chunk.law_id,
                    article_number=chunk.article_number,
                    anchor=chunk.anchor,
                    text_paraphrased=chunk.text_paraphrased,
                    similarity=float(link.relevance),
                    source="pattern",
                )
            )
        return citations

    def _vector_lookup(
        self,
        finding: str,
        *,
        threshold: float,
        top_k: int,
    ) -> list[LegalCitation]:
        query_vector = embed_query(finding)

        # Cosine distance = 1 - cosine similarity. We want similarity ≥ threshold,
        # i.e. distance ≤ 1 - threshold.
        max_distance = 1.0 - threshold

        # When reranking, pull a deeper pool from pgvector and let the
        # cross-encoder reorder. The bi-encoder gives recall; the
        # cross-encoder gives ordering.
        use_reranker = reranker_enabled()
        pool_size = settings.RAG_RERANKER_POOL_SIZE if use_reranker else top_k

        queryset = (
            LegalChunk.objects.filter(corpus_version=self.corpus_version)
            .annotate(distance=CosineDistance("embedding", query_vector))
            .filter(distance__lte=max_distance)
            .order_by("distance")[:pool_size]
        )

        chunks = list(queryset)
        if use_reranker and chunks:
            scores = reranker_score(finding, [c.text_paraphrased for c in chunks])
            chunks = [c for _, c in sorted(zip(scores, chunks, strict=True), key=lambda x: -x[0])]
            chunks = chunks[:top_k]
        else:
            chunks = chunks[:top_k]

        citations: list[LegalCitation] = []
        for chunk in chunks:
            similarity = 1.0 - float(chunk.distance)
            citations.append(
                LegalCitation(
                    chunk_id=str(chunk.id),
                    law_id=chunk.law_id,
                    article_number=chunk.article_number,
                    anchor=chunk.anchor,
                    text_paraphrased=chunk.text_paraphrased,
                    similarity=similarity,
                    source="vector",
                )
            )
        return citations

    def _log_query(
        self,
        *,
        finding: str,
        threshold: float,
        top_k: int,
        chunks_returned: int,
        pattern_shortcut_used: bool,
        latency_ms: int,
    ) -> None:
        try:
            RagQueryLog.objects.create(
                query_hash=hashlib.sha256(finding.strip().lower().encode("utf-8")).hexdigest(),
                corpus_version=self.corpus_version,
                top_k=top_k,
                similarity_threshold=threshold,
                chunks_returned=chunks_returned,
                pattern_shortcut_used=pattern_shortcut_used,
                latency_ms=latency_ms,
            )
        except Exception as exc:  # pragma: no cover — telemetry must never break retrieval
            logger.warning("rag.query_log.persist_failed", error=str(exc))


def prune_rag_query_log(*, older_than_days: int | None = None) -> int:
    """Delete rag_query_log rows older than `older_than_days` days (default 90).

    Wired into a Celery-beat schedule by `corpus.tasks` (out of scope for
    Phase 1 — this helper is enough for ad-hoc invocation and tests).
    """

    days = older_than_days if older_than_days is not None else 90
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = RagQueryLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted
