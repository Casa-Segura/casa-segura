"""CS-086 + CS-089: pattern_legal_link and rag_query_log tables."""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("corpus", "0002_fk_doc_hnsw_immutability"),
    ]

    operations = [
        migrations.CreateModel(
            name="PatternLegalLink",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "finding_pattern",
                    models.CharField(
                        help_text="Finding category or rubric pattern key, e.g. 'tenant_rights_unwaivable'",
                        max_length=128,
                    ),
                ),
                ("law_id", models.CharField(max_length=64)),
                ("anchor", models.CharField(max_length=64)),
                (
                    "relevance",
                    models.FloatField(
                        default=1.0,
                        help_text="Relative weight when several patterns match the same finding (default 1.0)",
                    ),
                ),
                ("notes", models.TextField(blank=True, default="")),
            ],
            options={
                "verbose_name": "Pattern → Legal Chunk Link",
                "db_table": "pattern_legal_link",
            },
        ),
        migrations.AddConstraint(
            model_name="patternlegallink",
            constraint=models.UniqueConstraint(
                fields=("finding_pattern", "law_id", "anchor"),
                name="uq_pattern_legal_link_triple",
            ),
        ),
        migrations.AddIndex(
            model_name="patternlegallink",
            index=models.Index(fields=["finding_pattern"], name="idx_pattern_link_finding"),
        ),
        migrations.AddIndex(
            model_name="patternlegallink",
            index=models.Index(fields=["law_id", "anchor"], name="idx_pattern_link_chunk"),
        ),
        migrations.CreateModel(
            name="RagQueryLog",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "query_hash",
                    models.CharField(
                        help_text="SHA-256 of the normalised query string", max_length=64
                    ),
                ),
                ("top_k", models.PositiveSmallIntegerField()),
                ("similarity_threshold", models.FloatField()),
                ("chunks_returned", models.PositiveSmallIntegerField()),
                ("pattern_shortcut_used", models.BooleanField(default=False)),
                ("latency_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "corpus_version",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rag_query_logs",
                        to="corpus.corpusversion",
                    ),
                ),
            ],
            options={
                "verbose_name": "RAG Query Log",
                "verbose_name_plural": "RAG Query Logs",
                "db_table": "rag_query_log",
            },
        ),
        migrations.AddIndex(
            model_name="ragquerylog",
            index=models.Index(fields=["created_at"], name="idx_rag_log_created_at"),
        ),
        migrations.AddIndex(
            model_name="ragquerylog",
            index=models.Index(fields=["query_hash"], name="idx_rag_log_query_hash"),
        ),
    ]
