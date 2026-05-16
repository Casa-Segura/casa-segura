# corpus/ — Legal corpus + RAG (F3)

Owns the versioned legal corpus that backs every finding's citation and
the RAG retrieval used by the rubric engine (F4).

## Entities (DOMAIN_MODEL §3.4–§3.6)

| Entity | Persistence | Purpose |
|---|---|---|
| `CorpusVersion` | Catalog (immutable; `is_active` singleton) | Version stamp of a corpus snapshot |
| `LegalDocument` | Catalog | One full law per `(law_id, corpus_version)` |
| `LegalChunk` | Catalog | RAG retrieval unit (one article or sub-article) with a 384-dim embedding |

## Placeholder semantics (CS-034)

Until F3 ingestion lands, the placeholder corpus seeded by

```bash
make seed-corpus
# or: python manage.py seed_corpus_version --activate
```

exists for one reason: **unblock the foreign key**
`ContractAnalysis.corpus_version`. The row has:

- `version = <today's UTC date in YYYY-MM-DD>` (overridable via `--catalog-version`)
- `laws_count = 0`, `articles_count = 0`, `chunks_count = 0`
- `manifest = {"laws": [], "placeholder": true}`
- `is_active = true` (after `--activate`)

**Implications while the placeholder is active:**

- `LegalDocument` and `LegalChunk` tables are intentionally empty. Any
  RAG retrieval call MUST return an empty result and surface the
  no-context branch of the rubric engine (configurable per criterion).
- Findings produced against the placeholder corpus carry no
  `LegalReference[]` — only the contract-clause evidence.
- The placeholder counts as a real `CorpusVersion` for reproducibility:
  `ContractAnalysis.corpus_version` stays valid forever and the
  `reject_catalog_mutation` trigger forbids mutating it.

## Replacing the placeholder (when F3 lands)

1. Run the F3 ingestion command (TBD) which INSERTs a NEW
   `CorpusVersion` row plus the matching `LegalDocument` and
   `LegalChunk` rows. **Never UPDATE** the placeholder; the
   immutability trigger will reject it.
2. Flip `is_active` atomically:
   ```sql
   BEGIN;
   UPDATE corpus_version SET is_active = false WHERE is_active = true;
   UPDATE corpus_version SET is_active = true  WHERE version = '<new>';
   COMMIT;
   ```
3. New analyses pick up the active version at the start of their
   pipeline. In-flight analyses keep the version stamped at submission
   time.

## Indexes (CS-030)

- `legal_chunk_embedding_hnsw_idx` — HNSW with `vector_cosine_ops`,
  `m=16, ef_construction=64` for dev/CI. Prod is expected to
  `ANALYZE` and rebuild with larger values.
- `idx_legal_chunk_tags`, `idx_legal_chunk_relevance` — GIN over the
  filter arrays.
- `idx_legal_chunk_corpus_version`, `idx_legal_chunk_law_id` — btree.
- `idx_ldoc_corpus_version` — btree on `legal_document`.
- Composite FK `fk_legal_chunk_document`:
  `legal_chunk(law_id, corpus_version) → legal_document(law_id, corpus_version) ON DELETE CASCADE`.

## References

- [PRD F3 — Corpus & RAG](../../docs/Casa%20Segura%20Formal%20PRDs/PRD_F3_CORPUS_Y_RAG.md)
- [Domain model §3.4–§3.6](../../docs/Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md)
- [ADR-0004 — Versioning strategy](../../docs/adr/ADR-0004-versioning.md)
