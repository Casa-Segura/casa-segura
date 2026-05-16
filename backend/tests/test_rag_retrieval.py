"""CS-085 / CS-086 / CS-089: retrieval service + pattern shortcut + logging.

We seed a tiny in-memory corpus with two chunks whose embeddings are
hand-crafted unit vectors so cosine distance is deterministic. No real
sentence-transformers calls happen in this suite.
"""

from __future__ import annotations

import uuid

import pytest

from corpus.application.retrieval import LegalCitationService
from corpus.application.tags import normalize_tag
from corpus.infrastructure.django.models import (
    CorpusVersion,
    LegalChunk,
    LegalDocument,
    PatternLegalLink,
    RagQueryLog,
)

EMBED_DIM = 384


def _unit_vector(direction: int) -> list[float]:
    """Return a 384-dim vector with `1.0` at `direction` and 0 elsewhere."""

    v = [0.0] * EMBED_DIM
    v[direction] = 1.0
    return v


@pytest.fixture
def seeded_corpus(db):
    from django.utils import timezone

    version = CorpusVersion.objects.create(
        version="test-v1",
        released_at=timezone.now(),
        laws_count=1,
        articles_count=2,
        chunks_count=2,
        manifest={"laws": []},
        is_active=True,
    )
    LegalDocument.objects.create(
        law_id="ley-inquilinato",
        corpus_version=version,
        title="Ley de Inquilinato",
    )
    chunk_a = LegalChunk.objects.create(
        id=uuid.uuid4(),
        law_id="ley-inquilinato",
        corpus_version=version,
        article_number="Art. 4",
        anchor="art-4",
        text_paraphrased="Cada contrato de arrendamiento debe constar por escrito.",
        text_verbatim="",
        embedding=_unit_vector(0),
        tags=["arrendamiento"],
        relevance_for_findings=[],
    )
    chunk_b = LegalChunk.objects.create(
        id=uuid.uuid4(),
        law_id="ley-inquilinato",
        corpus_version=version,
        article_number="Art. 2",
        anchor="art-2",
        text_paraphrased="Los derechos del inquilino son irrenunciables.",
        text_verbatim="",
        embedding=_unit_vector(1),
        tags=["irrenunciable"],
        relevance_for_findings=[],
    )
    return version, chunk_a, chunk_b


def test_pattern_shortcut_skips_vector_search(seeded_corpus, monkeypatch):
    version, _, _ = seeded_corpus
    PatternLegalLink.objects.create(
        finding_pattern=normalize_tag("required_clauses_present"),
        law_id="ley-inquilinato",
        anchor="art-4",
        relevance=0.95,
    )

    def _exploding_embed(text):
        raise AssertionError("vector path must not run when pattern matches")

    monkeypatch.setattr("corpus.application.retrieval.embed_query", _exploding_embed)

    service = LegalCitationService(corpus_version=version)
    citations = service.retrieve_legal_basis(
        finding="No hay contrato escrito",
        finding_pattern="required_clauses_present",
    )
    assert len(citations) == 1
    assert citations[0].source == "pattern"
    assert citations[0].law_id == "ley-inquilinato"
    assert citations[0].anchor == "art-4"
    # CS-089: every retrieval call logs.
    assert RagQueryLog.objects.count() == 1
    assert RagQueryLog.objects.first().pattern_shortcut_used is True


def test_vector_search_respects_threshold(seeded_corpus, monkeypatch):
    version, chunk_a, _ = seeded_corpus
    monkeypatch.setattr("corpus.application.retrieval.embed_query", lambda text: _unit_vector(0))

    service = LegalCitationService(corpus_version=version)
    citations = service.retrieve_legal_basis(finding="contrato escrito", threshold=0.65)
    assert len(citations) == 1
    assert citations[0].chunk_id == str(chunk_a.id)
    assert citations[0].similarity >= 0.65


def test_vector_search_returns_empty_when_threshold_too_high(seeded_corpus, monkeypatch):
    version, _, _ = seeded_corpus
    monkeypatch.setattr(
        "corpus.application.retrieval.embed_query",
        lambda text: [1.0 / EMBED_DIM**0.5] * EMBED_DIM,  # cosine ~ 1/sqrt(dim)
    )

    service = LegalCitationService(corpus_version=version)
    citations = service.retrieve_legal_basis(finding="anything", threshold=0.99)
    assert citations == []
