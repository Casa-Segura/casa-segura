"""CS-032 — negative FK-order example for factory / ORM discipline."""

from __future__ import annotations

import uuid

import pytest
from django.db import IntegrityError

from corpus.domain.enums import SeverityHint
from corpus.infrastructure.django.models import EMBEDDING_DIM, LegalChunk


def _zero_embedding() -> list[float]:
    return [0.0] * EMBEDDING_DIM


@pytest.mark.django_db(transaction=True)
def test_creating_chunk_without_valid_corpus_version_surfaces_fk_message() -> None:
    """AC3: inserting a child before its parent FK exists fails with a helpful DB error."""
    missing = "no-such-corpus-v9999"
    with pytest.raises(IntegrityError) as excinfo:
        LegalChunk.objects.create(
            id=uuid.uuid4(),
            law_id="orphan-law",
            corpus_version_id=missing,
            article_number="Art. 1",
            anchor="art-1",
            text_paraphrased="x",
            text_verbatim="",
            embedding=_zero_embedding(),
            tags=[],
            relevance_for_findings=[],
            severity_hint=SeverityHint.YELLOW.value,
        )
    msg = str(excinfo.value).lower()
    assert "corpus_version" in msg or "foreign key" in msg or "fk" in msg
