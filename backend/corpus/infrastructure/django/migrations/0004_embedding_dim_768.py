"""Embedding dimensionality bump 384 → 768 (CS-087 follow-up).

Switches `legal_chunk.embedding` from `vector(384)` (MiniLM-L12-v2) to
`vector(768)` (multilingual-e5-base). Cross-lingual MiniLM produced
Top-1 ~0.06 on the eval set; e5-base with `passage:`/`query:` prefixes
clears the bar.

Operationally:
  1. Drop the existing HNSW index (it is bound to the column dimension).
  2. Delete `legal_chunk` rows (they were embedded at 384 dims and are
     incompatible — re-ingestion will regenerate them).
  3. Delete `legal_document` rows in the same sweep (chunks FK to docs
     via composite; cascading from the corpus side is blocked by the
     immutability trigger on `corpus_version`).
  4. Alter the column type to `vector(768)`.
  5. Recreate the HNSW index with `vector_cosine_ops`.

`corpus_version` rows are retained — the immutability trigger blocks
DELETE on that table, and the activation flow flips `is_active` to
move forward.
"""

from __future__ import annotations

from django.db import migrations


DROP_HNSW = "DROP INDEX IF EXISTS legal_chunk_embedding_hnsw_idx;"
RECREATE_HNSW = """
CREATE INDEX IF NOT EXISTS legal_chunk_embedding_hnsw_idx
  ON legal_chunk
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
"""

WIPE_CHUNKS = "DELETE FROM legal_chunk;"
WIPE_DOCS = "DELETE FROM legal_document;"

ALTER_COLUMN_UP = (
    "ALTER TABLE legal_chunk "
    "ALTER COLUMN embedding TYPE vector(768) USING NULL;"
)
ALTER_COLUMN_DOWN = (
    "ALTER TABLE legal_chunk "
    "ALTER COLUMN embedding TYPE vector(384) USING NULL;"
)


class Migration(migrations.Migration):
    dependencies = [
        ("corpus", "0003_pattern_link_and_rag_log"),
    ]

    operations = [
        migrations.RunSQL(sql=DROP_HNSW, reverse_sql=RECREATE_HNSW),
        migrations.RunSQL(sql=WIPE_CHUNKS, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=WIPE_DOCS, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=ALTER_COLUMN_UP, reverse_sql=ALTER_COLUMN_DOWN),
        migrations.RunSQL(sql=RECREATE_HNSW, reverse_sql=DROP_HNSW),
    ]
