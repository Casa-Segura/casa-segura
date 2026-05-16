"""CS-026 + CS-030 follow-ups for corpus.

Adds:
  - Composite FK `legal_chunk(law_id, corpus_version) -> legal_document(law_id, corpus_version)`
    ON DELETE CASCADE, named `fk_legal_chunk_document`. PRD §3.6 says law_id is a FK; the
    only candidate key on legal_document is the composite (law_id, corpus_version)
    (`uq_legal_document_law_corpus` from 0001), so the FK is composite. Django ORM
    has no native composite-FK type; we emit it via RunSQL.
  - HNSW index on `legal_chunk.embedding` using `vector_cosine_ops`. CI/dev use
    smaller m/ef_construction to keep build cheap; prod is expected to ANALYZE
    and rebuild with larger values per pgvector ops guidance.
  - Trigger `legal_chunk_corpus_immutable` (function defined in
    platform_core.0002) so corpus_version catalog rows cannot be mutated
    beyond `is_active`.
"""

from __future__ import annotations

from django.db import migrations


FK_ADD = """
ALTER TABLE legal_chunk
  ADD CONSTRAINT fk_legal_chunk_document
  FOREIGN KEY (law_id, corpus_version)
  REFERENCES legal_document (law_id, corpus_version)
  ON DELETE CASCADE
  DEFERRABLE INITIALLY DEFERRED;
"""
FK_DROP = "ALTER TABLE legal_chunk DROP CONSTRAINT IF EXISTS fk_legal_chunk_document;"

HNSW_ADD = """
CREATE INDEX IF NOT EXISTS legal_chunk_embedding_hnsw_idx
  ON legal_chunk
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
"""
HNSW_DROP = "DROP INDEX IF EXISTS legal_chunk_embedding_hnsw_idx;"

CORPUS_TRIGGER_ADD = """
CREATE TRIGGER corpus_version_immutable
  BEFORE UPDATE OR DELETE ON corpus_version
  FOR EACH ROW EXECUTE FUNCTION reject_catalog_mutation();
"""
CORPUS_TRIGGER_DROP = "DROP TRIGGER IF EXISTS corpus_version_immutable ON corpus_version;"


class Migration(migrations.Migration):
    dependencies = [
        ("corpus", "0001_initial"),
        ("platform_core", "0002_immutability_function_and_views"),
    ]

    operations = [
        migrations.RunSQL(sql=FK_ADD, reverse_sql=FK_DROP),
        migrations.RunSQL(sql=HNSW_ADD, reverse_sql=HNSW_DROP),
        migrations.RunSQL(sql=CORPUS_TRIGGER_ADD, reverse_sql=CORPUS_TRIGGER_DROP),
    ]
