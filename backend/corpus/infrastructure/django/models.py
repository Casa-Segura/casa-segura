"""Legal corpus tables — CorpusVersion + LegalDocument + LegalChunk.

DOMAIN_MODEL §3.4, §3.5, §3.6. Schema declared by F8, owned by corpus/.
Versioned catalog with cosine vector search on `LegalChunk.embedding` (HNSW
index added in CS-030)."""

from __future__ import annotations

from typing import ClassVar

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Q
from pgvector.django import VectorField

from common.infrastructure.django.models import ModelWithTimeStamps
from corpus.domain.enums import LegalDocumentStatus, SeverityHint

EMBEDDING_DIM = 1024  # intfloat/multilingual-e5-large


class CorpusVersion(ModelWithTimeStamps):
    """Version of the legal corpus used in a specific retrieval. Immutable catalog (DOMAIN §3.4)."""

    version = models.CharField(
        max_length=32,
        primary_key=True,
        help_text="Versioned by date or by corpus commit hash, e.g. 2026-05-10",
    )
    released_at = models.DateTimeField(help_text="When this corpus version was released")
    laws_count = models.PositiveIntegerField(help_text="Total laws in this version")
    articles_count = models.PositiveIntegerField(help_text="Total indexed articles")
    chunks_count = models.PositiveIntegerField(help_text="Total vectorized chunks")
    manifest = models.JSONField(help_text="List of included laws with their identifiers")
    changelog = models.TextField(blank=True, default="", help_text="Summary of changes")
    is_active = models.BooleanField(
        default=False,
        help_text="Exactly one corpus version may be active at a time",
    )

    class Meta:
        db_table = "corpus_version"
        verbose_name = "Corpus Version"
        verbose_name_plural = "Corpus Versions"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="uq_corpus_version_active_singleton",
            ),
        ]

    def __str__(self) -> str:
        return f"CorpusVersion({self.version})"


class LegalDocument(ModelWithTimeStamps):
    """Full legal document of the corpus (one whole law). DOMAIN §3.5.

    A given `law_id` may exist in multiple corpus versions with changes; the uniqueness
    is on the pair `(law_id, corpus_version)`."""

    law_id = models.CharField(
        max_length=64,
        help_text="Slug, e.g. ley-inquilinato",
    )
    corpus_version = models.ForeignKey(
        CorpusVersion,
        on_delete=models.PROTECT,
        related_name="documents",
        db_column="corpus_version",
        help_text="Corpus version this document snapshot belongs to",
    )
    title = models.TextField(help_text="Official title")
    short_title = models.CharField(max_length=128, blank=True, default="", help_text="Short title for citations")
    decree = models.CharField(max_length=128, blank=True, default="", help_text="Decree number and date")
    issued_at = models.DateField(null=True, blank=True, help_text="Original issuance date")
    official_gazette = models.CharField(
        max_length=256, blank=True, default="", help_text="Reference to the official gazette"
    )
    last_verified = models.DateField(null=True, blank=True, help_text="Last date verified against official source")
    source_url = models.URLField(max_length=512, blank=True, default="", help_text="URL of the official source")
    status = models.CharField(
        max_length=32,
        choices=LegalDocumentStatus.choices,
        default=LegalDocumentStatus.IN_FORCE,
        help_text="Current status of the law",
    )
    subject = models.CharField(max_length=128, blank=True, default="", help_text="Area of law")

    class Meta:
        db_table = "legal_document"
        verbose_name = "Legal Document"
        verbose_name_plural = "Legal Documents"
        constraints = [
            models.UniqueConstraint(
                fields=["law_id", "corpus_version"],
                name="uq_legal_document_law_corpus",
            ),
            models.CheckConstraint(
                check=Q(status__in=[s.value for s in LegalDocumentStatus]),
                name="ck_legal_document_status_enum",
            ),
        ]
        indexes = [
            models.Index(fields=["corpus_version"], name="idx_ldoc_corpus_version"),
        ]

    def __str__(self) -> str:
        return f"LegalDocument({self.law_id}@{self.corpus_version_id})"


class LegalChunk(ModelWithTimeStamps):
    """Indexable corpus fragment, typically an article or sub-article. RAG retrieval unit (DOMAIN §3.6).

    Embedding generated with `intfloat/multilingual-e5-large` (1024 dim) using the
    `passage: ` input prefix at ingest and `query: ` at retrieve.
    HNSW index with vector_cosine_ops applied in CS-030."""

    id = models.UUIDField(primary_key=True)
    law_id = models.CharField(
        max_length=64,
        help_text="Slug of the parent LegalDocument",
    )
    corpus_version = models.ForeignKey(
        CorpusVersion,
        on_delete=models.PROTECT,
        related_name="chunks",
        db_column="corpus_version",
        help_text="Corpus version this chunk belongs to",
    )
    article_number = models.CharField(max_length=32, help_text="E.g. 'Art. 4', 'Art. 18'")
    anchor = models.CharField(max_length=64, help_text="Anchor slug, e.g. 'art-4'")
    text_paraphrased = models.TextField(help_text="Curated paraphrase shown to the user")
    text_verbatim = models.TextField(blank=True, default="", help_text="Verbatim article text (may be long)")
    embedding = VectorField(dimensions=EMBEDDING_DIM, help_text="1024-dim e5-large embedding of the paraphrased text")
    tags = ArrayField(
        models.CharField(max_length=64),
        default=list,
        blank=True,
        help_text="Filter tags, e.g. ['warranty','eviction']",
    )
    relevance_for_findings = ArrayField(
        models.CharField(max_length=64),
        default=list,
        blank=True,
        help_text="Finding categories where this chunk applies",
    )
    severity_hint = models.CharField(
        max_length=16,
        choices=SeverityHint.choices,
        null=True,
        blank=True,
        help_text="Suggested severity if the contract fails this article",
    )

    class Meta:
        db_table = "legal_chunk"
        verbose_name = "Legal Chunk"
        verbose_name_plural = "Legal Chunks"
        constraints = [
            models.UniqueConstraint(
                fields=["corpus_version", "law_id", "anchor"],
                name="uq_legal_chunk_corpus_law_anchor",
            ),
        ]
        indexes = [
            models.Index(fields=["corpus_version"], name="idx_legal_chunk_corpus_version"),
            models.Index(fields=["law_id"], name="idx_legal_chunk_law_id"),
            GinIndex(fields=["tags"], name="idx_legal_chunk_tags"),
            GinIndex(fields=["relevance_for_findings"], name="idx_legal_chunk_relevance"),
        ]

    def __str__(self) -> str:
        return f"LegalChunk({self.law_id} {self.article_number}@{self.corpus_version_id})"


class PatternLegalLink(models.Model):
    """Rubric-finding → legal chunk shortcut (CS-086).

    Lets retrieval skip vector search when a finding is already known to
    map to a specific article in the corpus. Pre-populated from
    `pattern_legal_link.yaml` (curated content; not in scope for Phase 1).

    The link points at a specific `(law_id, anchor)` so it survives
    re-chunking as long as anchors are stable (CS-081 keeps them stable
    across same-version re-ingestions).
    """

    id = models.BigAutoField(primary_key=True)
    finding_pattern = models.CharField(
        max_length=128,
        help_text="Finding category or rubric pattern key, e.g. 'tenant_rights_unwaivable'",
    )
    law_id = models.CharField(max_length=64)
    anchor = models.CharField(max_length=64)
    relevance = models.FloatField(
        default=1.0,
        help_text="Relative weight when several patterns match the same finding (default 1.0)",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "pattern_legal_link"
        verbose_name = "Pattern → Legal Chunk Link"
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["finding_pattern", "law_id", "anchor"],
                name="uq_pattern_legal_link_triple",
            ),
        ]
        indexes: ClassVar = [
            models.Index(fields=["finding_pattern"], name="idx_pattern_link_finding"),
            models.Index(fields=["law_id", "anchor"], name="idx_pattern_link_chunk"),
        ]

    def __str__(self) -> str:
        return f"PatternLegalLink({self.finding_pattern} → {self.law_id}#{self.anchor})"


class RagQueryLog(models.Model):
    """Audit log for RAG retrieval (CS-089).

    Stores the hashed query, corpus version, top_k, threshold and the
    number of chunks returned. The actual finding text is hashed (not
    persisted) so the table is safe to keep across the 90-day TTL.

    A Celery-beat job (`corpus.tasks.prune_rag_query_log`) purges rows
    older than `RAG_QUERY_LOG_TTL_DAYS` (default 90).
    """

    id = models.BigAutoField(primary_key=True)
    query_hash = models.CharField(max_length=64, help_text="SHA-256 of the normalised query string")
    corpus_version = models.ForeignKey(
        CorpusVersion,
        on_delete=models.PROTECT,
        related_name="rag_query_logs",
    )
    top_k = models.PositiveSmallIntegerField()
    similarity_threshold = models.FloatField()
    chunks_returned = models.PositiveSmallIntegerField()
    pattern_shortcut_used = models.BooleanField(default=False)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rag_query_log"
        verbose_name = "RAG Query Log"
        verbose_name_plural = "RAG Query Logs"
        indexes: ClassVar = [
            models.Index(fields=["created_at"], name="idx_rag_log_created_at"),
            models.Index(fields=["query_hash"], name="idx_rag_log_query_hash"),
        ]

    def __str__(self) -> str:
        return f"RagQueryLog({self.query_hash[:8]}@{self.created_at:%Y-%m-%d})"
