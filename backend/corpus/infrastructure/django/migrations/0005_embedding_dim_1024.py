"""Embedding dimensionality bump 768 → 1024 (CS-087 follow-up #2).

e5-base (768) lifted Top-1 from 0.06 → 0.30; scores clustered in
0.83–0.86 with poor discrimination on tenant_rights / required_clauses.
Switching to e5-large (1024) for stronger retrieval semantics.

Same operational pattern as 0004:
  1. Drop HNSW.
  2. Wipe `legal_chunk` + `legal_document` (incompatible dim).
  3. Alter column to vector(1024).
  4. Recreate HNSW.
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
    "ALTER COLUMN embedding TYPE vector(1024) USING NULL;"
)
ALTER_COLUMN_DOWN = (
    "ALTER TABLE legal_chunk "
    "ALTER COLUMN embedding TYPE vector(768) USING NULL;"
)


class Migration(migrations.Migration):
    dependencies = [
        ("corpus", "0004_embedding_dim_768"),
    ]

    operations = [
        migrations.RunSQL(sql=DROP_HNSW, reverse_sql=RECREATE_HNSW),
        migrations.RunSQL(sql=WIPE_CHUNKS, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=WIPE_DOCS, reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL(sql=ALTER_COLUMN_UP, reverse_sql=ALTER_COLUMN_DOWN),
        migrations.RunSQL(sql=RECREATE_HNSW, reverse_sql=DROP_HNSW),
    ]
