"""CS-030 acceptance proofs: HNSW index usage + v_retention_status overdue counts."""

from __future__ import annotations

import uuid

import pytest
from django.db import connection, transaction
from django.utils import timezone

from corpus.infrastructure.django.models import CorpusVersion, EMBEDDING_DIM, LegalChunk, LegalDocument
from platform_core.infrastructure.django.models import ContractAnalysis
from tests.factories import ContractAnalysisFactory, age_to


def _zero_vector() -> list[float]:
    return [0.0] * EMBEDDING_DIM


def _zero_vector_sql() -> str:
    return "[" + ",".join("0" for _ in range(EMBEDDING_DIM)) + "]"


@pytest.mark.django_db(transaction=True)
def test_explain_vector_search_uses_hnsw_index() -> None:
    """AC1: cosine-distance ORDER BY should hit the HNSW index, not seq scan."""
    version = CorpusVersion.objects.create(
        version="cs030-explain-v1",
        released_at=timezone.now(),
        laws_count=1,
        articles_count=2,
        chunks_count=1,
        manifest={"laws": []},
        is_active=True,
    )
    LegalDocument.objects.create(
        law_id="ley-cs030",
        corpus_version=version,
        title="Test",
    )
    LegalChunk.objects.create(
        id=uuid.uuid4(),
        law_id="ley-cs030",
        corpus_version=version,
        article_number="Art. 1",
        anchor="art-1",
        text_paraphrased="x",
        text_verbatim="",
        embedding=_zero_vector(),
        tags=[],
        relevance_for_findings=[],
    )

    vec = _zero_vector_sql()
    with transaction.atomic():
        with connection.cursor() as cursor:
            # Prefer index path for planner proof (fixture DB may hold many rows).
            cursor.execute("SET LOCAL enable_seqscan TO OFF")
            cursor.execute(
                """
                EXPLAIN (FORMAT TEXT)
                SELECT id FROM legal_chunk
                ORDER BY embedding <=> %s::vector
                LIMIT 3
                """,
                [vec],
            )
            plan = "\n".join(row[0] for row in cursor.fetchall()).lower()
    assert "hnsw" in plan or "legal_chunk_embedding" in plan or "legal_chunk_embedding_hnsw" in plan


@pytest.mark.django_db(transaction=True)
def test_v_retention_status_analyses_overdue_anonymization() -> None:
    """AC4: overdue anonymization row drives analyses_overdue_anonymization > 0."""
    analysis: ContractAnalysis = ContractAnalysisFactory()
    old = timezone.now() - timezone.timedelta(days=91)
    age_to(old, on=analysis, field="created_at")
    analysis.refresh_from_db()
    assert analysis.anonymized_at is None

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT analyses_overdue_anonymization FROM v_retention_status",
        )
        row = cursor.fetchone()
    assert row is not None
    assert row[0] >= 1
