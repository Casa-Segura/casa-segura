# Evaluation Coverage — F3: Legal Corpus & Citation Retrieval

> Generated: 2026-05-15

---

## PRD Contradictions

None detected internal to PRD_F3. Cross-PRD items handled in `_shared/GLOBAL_ASSUMPTIONS.md`.

---

## Coverage Matrix

| PRD Requirement | Covered By | Status |
|---|---|---|
| US-01: ingest a corpus version | `IMPLEMENTATION_PLAN.md` Story US-01 + Flow 1 + Stage 7 migration | COVERED |
| US-02: build embeddings | `IMPLEMENTATION_PLAN.md` Story US-02 + adapter code | COVERED |
| US-03: F4 retrieval API | `IMPLEMENTATION_PLAN.md` Story US-03 + `COMPLETE_FLOWS.md` Flow 3 | COVERED |
| US-04: cite-or-stay-silent | `IMPLEMENTATION_PLAN.md` Story US-04 + `DESIGN_PATTERNS.md` Strict Threshold | COVERED |
| US-05: versioning | Versioned Immutable Catalog pattern; partial unique index | COVERED |
| US-06: operator audit | `IMPLEMENTATION_PLAN.md` Story US-06 + `corpus_audit` command | COVERED |
| BR-01 invariant cite-or-stay-silent | `DESIGN_PATTERNS.md` + `LegalCitationService.retrieve_legal_basis` | COVERED |
| BR-02 embed paraphrase, not verbatim | Adapter encodes `text_paraphrased`; verbatim never embedded | COVERED |
| BR-03 corpus immutability | Schema designed so chunks key on `(corpus_version, ...)`; no UPDATE path | COVERED |
| BR-04 paraphrases human-curated | Ingestion does not generate; only consumes | COVERED |
| BR-05 verbatim optional | `text_verbatim` nullable | COVERED |
| BR-06 threshold default 0.65 | `RAG_DEFAULT_THRESHOLD` env var | COVERED |
| BR-07 prefer_anchors priority | `LegalChunkRepository.cosine_search` two-phase | COVERED |
| BR-08 tag normalization | `ParsedArticle.tags` lowercased & accent-stripped in parser | COVERED |
| BR-09 model change → re-ingest | Documented in ops runbook; new model → new version | COVERED |
| BR-10 markdown source of truth | `LegalDocument.file_path` + `content_hash` | COVERED |
| BR-11 severity_hint informational | F4 free to contradict | COVERED |
| BR-12 query log 90 day TTL | `RagQueryLog.expires_at` + F8 cron | COVERED |
| Data model `corpus_version` | ERD + IMPLEMENTATION_PLAN Stage 7 | COVERED |
| Data model `legal_document` | ERD + IMPLEMENTATION_PLAN Stage 7 | COVERED |
| Data model `legal_chunk` | ERD + IMPLEMENTATION_PLAN Stage 7 | COVERED |
| Data model `rag_query_log` | ERD + IMPLEMENTATION_PLAN Stage 7 | COVERED |
| Recognized regex patterns (PRD §6.2) | `article_regex.py` | COVERED |
| Corpus repository structure (PRD §6.4) | `IMPLEMENTATION_PLAN.md` directory layout | COVERED |
| Mgmt commands (PRD §6.5) | All five commands listed | COVERED |
| Internal QA endpoint | `InternalRagQueryView` | COVERED |
| NFR P50 ≤ 50 ms, P95 ≤ 150 ms | Metrics + HNSW index | COVERED (instrumented) |
| NFR ≥ 70% findings with citation | Tracked via `f3_retrieve_results_total{outcome}` | COVERED (instrumented) |
| NFR top-1 precision > 85% | Manual QA against labeled set; metrics enable measurement | PARTIAL (depends on labeled set) |

---

## Critical Points

1. **Corpus immutability** — published versions never mutate; the schema enforces this via `(corpus_version, law_id, anchor)` UNIQUE and the application never UPDATEs a chunk row.
2. **Embedding model lock-in** — switching the model invalidates every existing embedding. Documented operational procedure: ingest a new corpus version with the new model; old versions remain queryable with their old vectors.
3. **HNSW vs. IVF index tuning** — HNSW is preferred at MVP scale (< 5k chunks); revisit if the corpus grows to 50k+ chunks.
4. **Empty results UX** — F4 must clearly label findings without citations. The contract between F3 and F4 says "an empty list is a valid, expected response".

---

## Open Questions

**[Q-F3-01]: Threshold 0.65 universal?**
Source: PRD §10 Q-1.
Resolution: **Assumed default**. Per-criterion override available via `Criterion.legal_anchor` priority and per-call `threshold` param. Calibration left to QA.

**[Q-F3-02]: Should multiple law cites per finding be capped?**
Source: PRD §10 Q-2.
Resolution: **Assumed cap = 3 citations per finding** (F4's `top_k=3` default).

**[Q-F3-03]: Alert on zero results for a criterion?**
Source: PRD §10 Q-3.
Resolution: **Assumed**. Prometheus alert if `f3_retrieve_results_total{outcome="empty",criterion_id=X}` exceeds 50% in 24 h.

**[Q-F3-04]: Include doctrine / case law?**
Source: PRD §10 Q-4.
Resolution: **No** at MVP. Documented.

**[Q-F3-05]: Reform handling — per-chunk vs. per-corpus version?**
Source: PRD §10 Q-5.
Resolution: **Per-corpus version** at MVP. Simpler; correctness preserved. Per-chunk versioning deferred.

**[Q-F3-06]: Mechanism to deprecate a chunk?**
Source: PRD §10 Q-6.
Resolution: **Out of MVP**. Repealed articles flagged via the law's `status='repealed'`; the retrieval can filter by `LegalDocument.status` at query time.

**[Q-F3-07]: Curation process?**
Source: PRD §10 Q-7.
Resolution: **Assumed**: PR-review with a designated legal reviewer. Documented in `corpus/README.md`.

**[Q-F3-08]: Update paraphrases?**
Source: PRD §10 Q-8.
Resolution: **No in-place updates**. A paraphrase change is a new corpus version.

---

## Edge Cases to Validate

- A chunk's embedding norm differs from 1.0 by more than ε → ingestion warning, but does not block (the cosine distance still works on non-normalized vectors)
- Two chunks with very close embeddings (paraphrase near-duplicates) → returned in order of score; not deduplicated automatically
- A query with empty text → `EmbeddingFailed` raised; F4 handles
- A query with text exceeding 512 tokens → tokenizer truncates; documented in adapter
- Concurrent ingest of two versions → file locking via DB row-level locks on `corpus_version` insert prevents conflict; second concurrent ingest fails clean
- Corpus DB rebuild from files: `python manage.py corpus_ingest --version v --force` recreates all rows; test the round-trip preserves all data
- A finding text mentioning two articles ("Art. 12 LPC y Art. 1644 CC") → hybrid matches the first; future enhancement could match both

---

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-F3-01 | Embedding model behavior changes silently on upgrade | Pin version in `pyproject.toml`; warm-up self-test asserts reference vector match |
| R-F3-02 | Corpus authoring error (wrong paraphrase) → F4 emits incorrect citation | PR review; weekly audit lists most-cited chunks for spot review |
| R-F3-03 | HNSW index missing after restore | Migration is idempotent; runbook covers manual recreation |
| R-F3-04 | RagQueryLog grows unbounded | F8 cron cleans rows past `expires_at` (90 days) |
| R-F3-05 | Vector dimensions mismatch (e.g., model returns 768) | Embedding adapter asserts dim at startup |

---

## Cross-Validation Log

| Iteration | Discrepancies Found | Files Corrected |
|---|---|---|
| 1 | 0 | Aligned with Django 5.2 from the start |
| 2 | 0 | Field names, repository methods, commands consistent |
| 3 | 0 | Cross-references between ERD, class diagram, plan all match |
| 4 | 0 | Acceptance |

## PRD Alignment Log

| Iteration | PRD Items Checked | Misalignments | Coverage % |
|---|---|---|---|
| 1 | 26 | 0 | 100% |

---

**End of document.**
