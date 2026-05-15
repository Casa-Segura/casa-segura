# Complete Flows — F3: Legal Corpus & Citation Retrieval

> Generated: 2026-05-15

---

## Flow Index

| # | Flow Name | Type | Complexity |
|---|---|---|---|
| 1 | Operator ingests a new corpus version | Mgmt command | High |
| 2 | Operator activates a version | Mgmt command | Low |
| 3 | F4 retrieves citations (semantic) | Sync function call | High |
| 4 | F4 retrieves citations (exact via hybrid) | Sync function call | Low |
| 5 | F4 retrieves citations (empty result — cite-or-stay-silent) | Sync function call | Low |
| 6 | F6 looks up a chunk for "see verbatim" link | Sync function call | Low |
| 7 | Operator audits coverage | Mgmt command | Medium |
| 8 | QA tests a single retrieval via internal endpoint | DRF request | Low |

---

## Flow 1: Operator ingests a new corpus version

### Pre-conditions

- Operator has shell access to the production runtime (or runs via CI/CD)
- Markdown source under `corpus/laws/*.md` with valid YAML frontmatter
- Postgres reachable; `pgvector` extension installed
- Embedding model files downloaded under `EMBEDDING_MODEL_CACHE_DIR` (or downloadable from HF)

### Trigger

`python manage.py corpus_ingest --version 2026-05-10 --path ./corpus/laws/`

### Happy Path

**1. Command parses CLI args**
- `--version`, `--path`, optional `--force`

**2. Pre-check**
- `CorpusVersion.objects.filter(version=v).exists()` → exit code 1 with "version exists, use --force" if not forced
- If `--force`, the command does `DELETE FROM legal_chunk WHERE corpus_version=v`, `DELETE FROM legal_document WHERE corpus_version=v`, `DELETE FROM corpus_version WHERE version=v` then proceeds

**3. Discover files**
- `glob(path/*.md)` sorted by filename for deterministic order

**4. Parse files in a single transaction**
- `with transaction.atomic():`
- For each file:
  - `parsed = MarkdownCorpusParser.parse_file(file)`
  - Validate frontmatter (presence of `law_id`, `title`, `status`, `last_verified`); reject on missing required fields
  - `LegalDocument.objects.create(law_id=parsed.law_id, corpus_version=v, ...)`
  - Compute embeddings for all articles in a single batch via `EmbeddingModel.encode_batch`
  - For each article: `LegalChunk.objects.create(corpus_version=v, law_id=parsed.law_id, article_number=art.article_number, anchor=art.anchor, text_paraphrased=art.text_paraphrased, text_verbatim=art.text_verbatim, embedding=embedding, tags=art.tags, relevance_for_findings=art.relevance_for_findings, severity_hint=art.severity_hint)`
- Compute manifest: `{ "laws": [{"law_id": ..., "title": ..., "articles_count": ...}], "total_chunks": N }`
- `CorpusVersion.objects.create(version=v, laws_count=L, articles_count=A, chunks_count=C, manifest=..., changelog=..., is_active=False, created_by=os.getenv("USER"))`

**5. Audit log**
- Insert `PrivacyAuditLog(event_type='corpus_version_published', related_id=…, event_data={"version": v, "laws_count": L, "chunks_count": C}, triggered_by=os.getenv("USER"))`

**6. Print summary**
- "Ingested version 2026-05-10: 9 laws, 152 articles. NOT active yet — run corpus_activate."

### Error Scenarios

| ID | Condition | Outcome |
|---|---|---|
| E-1 | Version exists, no --force | Exit code 1 with message |
| E-2 | YAML frontmatter missing required field | Transaction rollback; error names file and missing field |
| E-3 | Article body lacks `### Art. N` heading | Warning (chunk skipped), recorded in report |
| E-4 | Embedding model fails to load | Exit code 2; ops alert |
| E-5 | Postgres connection drops mid-ingest | Transaction rollback; safe to retry |
| E-6 | Duplicate anchor within the same law | Hard error; cannot have two `art-12` in `ley-proteccion-consumidor` for one version |

---

## Flow 2: Operator activates a version

### Trigger

`python manage.py corpus_activate --version 2026-05-10`

### Happy Path

1. Open transaction
2. `CorpusVersion.objects.filter(is_active=True).update(is_active=False)`
3. `CorpusVersion.objects.filter(version=v).update(is_active=True)` → 1 row updated; if 0, abort
4. Commit
5. Audit log entry
6. Print success

### Error

- Version not found → exit code 1 "Unknown version 2026-05-10"
- Concurrent activation race → the partial unique index prevents two active rows; the second update raises `IntegrityError`; the command retries once then fails clean

---

## Flow 3: F4 retrieves citations (semantic)

### Pre-conditions

- An active corpus version exists, the analysis's `corpus_version` is set
- F4 has a finding text under evaluation

### Trigger

F4 calls `legal_citation_service.retrieve_legal_basis(...)`.

### Happy Path

**1. F4 → Service**
- `retrieve_legal_basis(finding_text="...", corpus_version="2026-05-10", top_k=3, threshold=0.65, prefer_anchors=criterion.legal_anchor, criterion_id="B7", analysis_id=A)`

**2. Hybrid check**
- `HybridMatcher.find_exact_anchor(finding_text, "2026-05-10")` returns `None`

**3. Encode**
- `q = embedding_model.encode(finding_text)` → 384-d L2-normalized vector

**4. Repository query**
```sql
SELECT lc.*, ld.title AS law_title, 1 - (lc.embedding <=> $1::vector) AS similarity
FROM legal_chunk lc
JOIN legal_document ld ON ld.law_id = lc.law_id AND ld.corpus_version = lc.corpus_version
WHERE lc.corpus_version = $2
  AND ( $3::text[] IS NULL OR lc.anchor = ANY($3) )
  AND ( $4::text[] IS NULL OR lc.tags && $4 )
ORDER BY lc.embedding <=> $1
LIMIT $5;
```

**5. Two-phase priority**
- First try with `prefer_anchors` set; if returns ≥ 1 result above threshold, use it
- Else re-run with `prefer_anchors = NULL`

**6. Build LegalReference list**
- Filter by threshold (`similarity ≥ 0.65`)
- Sort by descending similarity (already from query)
- Wrap each row in `LegalReference`

**7. Log**
- `RagQueryLog(query_text_hash=salt+sha256(finding_text), corpus_version, top_k, threshold, filter_tags, results_count_total=raw, results_count_above_threshold=final, top_score, criterion_id, analysis_id)`

**8. Return** to F4

### Post-conditions

- 0 or more `LegalReference` objects ready to embed in `Finding.legal_basis`
- One row in `rag_query_log` (TTL 90 days)
- No mutation to corpus tables

### Error Scenarios

| ID | Condition | Outcome |
|---|---|---|
| E-1 | Corpus version not found | Raises `CorpusVersionNotFound` (F4 surface this as `unverifiable_legal` and continue) |
| E-2 | Embedding model unavailable | Raises `EmbeddingFailed`; F4 fallback emits finding without citation |
| E-3 | DB unreachable | Raises; F4's task is auto-retried by Celery |

---

## Flow 4: F4 retrieves citations (exact)

### Trigger

Finding text contains an explicit article reference (e.g., "Art. 12 LPC").

### Happy Path

1. `HybridMatcher` regex matches, extracts `(law_id, anchor)`
2. `LegalChunkRepository.get_by_anchor("ley-proteccion-consumidor", "art-12", "2026-05-10")` returns the chunk
3. `LegalReference` built with `similarity_score=1.0`
4. Log entry with `top_score=1.0`
5. Return

### Notes

- The regex list is in `corpus/infrastructure/parsing/article_regex.py`, mirroring PRD §6.2
- If the regex matches but the chunk does not exist in the requested version (corpus drift), the result falls through to semantic search

---

## Flow 5: F4 retrieves citations (empty — cite-or-stay-silent)

### Trigger

Top similarity is below threshold.

### Happy Path

1. Semantic search returns rows with scores [0.58, 0.52, 0.41]
2. Filter by 0.65 → empty list
3. Log entry with `results_count_above_threshold=0`, `top_score=0.58`
4. Return `[]`

### F4 behavior

- F4 emits the finding with `legal_basis=[]`
- F4 tags the finding `market_based` if the criterion is market-based (no `legal_anchor`)
- F4 tags the finding `unverifiable_legal` if the criterion has `legal_anchor` set but F3 didn't find a match (corpus gap)

---

## Flow 6: F6 looks up a chunk for "see verbatim"

### Trigger

The HTML report renders a finding's legal_basis. The user clicks "See full text".

### Happy Path

- Frontend calls a JSON endpoint `GET /r/{short_id}/legal/{anchor}` (served by F6, not F3 directly)
- F6 calls `legal_citation_service.get_chunk_by_anchor(law_id, anchor, analysis.corpus_version)`
- Returns `text_verbatim` if present; otherwise the paraphrase
- If chunk missing: 404

---

## Flow 7: Operator audits coverage

### Trigger

`python manage.py corpus_audit --version latest_active --export report.csv`

### Happy Path

1. Resolve `latest_active`
2. Read counts: laws, articles, chunks
3. Aggregate `rag_query_log` over the last 30 days: top-cited anchors, finding categories most often emptied
4. List chunks with `last_verified < NOW() - 6 months`
5. List chunks with empty `tags` or empty `relevance_for_findings`
6. Print + optionally write CSV

---

## Flow 8: QA tests retrieval via internal endpoint

### Trigger

`POST /v1/internal/rag/query` with `X-Internal-Auth`.

### Request

```json
{
    "finding_text": "El contrato exime al vendedor de saneamiento por evicción.",
    "corpus_version": "latest_active",
    "top_k": 5,
    "threshold": 0.65,
    "filter_tags": ["saneamiento", "vendedor"]
}
```

### Response

```json
{
    "corpus_version_resolved": "2026-05-10",
    "query_embedding_time_ms": 45,
    "search_time_ms": 12,
    "results": [
        {
            "chunk_id": "...",
            "law_id": "codigo-civil",
            "law_title": "Código Civil",
            "article": "Art. 1644",
            "anchor": "art-1644",
            "text_paraphrased": "...",
            "text_verbatim": "Art. 1644.- Es nulo todo pacto en que...",
            "similarity_score": 0.91,
            "tags": ["saneamiento", "evicción", "compraventa"],
            "severity_hint": "override_critical"
        }
    ],
    "results_count_total": 5,
    "results_count_above_threshold": 2
}
```

### Notes

- Returns the same shape used internally by F4, plus timing breakdown
- Still logs to `rag_query_log` but without `analysis_id`
- Rate-limited per IP

---

**End of document.**
