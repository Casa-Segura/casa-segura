# Interaction Diagrams — F3: Legal Corpus & Citation Retrieval

> Generated: 2026-05-15
> Companion: `SOLUTION_DIAGRAMS.md`

---

## Component Overview

```mermaid
graph TD
    MD[corpus/laws/*.md]
    Ingest[CorpusIngestionService]
    Cite[LegalCitationService]
    Emb[EmbeddingModel sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2]
    F4[F4 rubric engine]
    F6[F6 report generator]
    PG[(Postgres + pgvector HNSW)]
    Cmds[Mgmt commands]

    MD --> Cmds --> Ingest
    Ingest --> Emb
    Ingest --> PG
    F4 --> Cite
    F6 --> Cite
    Cite --> Emb
    Cite --> PG
```

---

## Flow: US-01 Ingest a corpus version

### Happy Path

```mermaid
sequenceDiagram
    actor Op as Operator
    participant Cmd as CorpusIngestCommand
    participant Svc as CorpusIngestionService
    participant Parser as MarkdownCorpusParser
    participant Emb as EmbeddingModel
    participant VRepo as CorpusVersionRepository
    participant DRepo as LegalDocumentRepository
    participant CRepo as LegalChunkRepository
    participant PG as Postgres

    Op->>Cmd: python manage.py corpus_ingest --version 2026-05-10 --path ./corpus/laws
    Cmd->>VRepo: get_by_version("2026-05-10")
    VRepo-->>Cmd: None
    Cmd->>Svc: ingest("2026-05-10", "./corpus/laws", force=False)
    Svc->>PG: BEGIN
    loop For each *.md in path
        Svc->>Parser: parse_file(file)
        Parser-->>Svc: ParsedDocument(frontmatter, articles)
        Svc->>Svc: validate frontmatter (law_id, status, last_verified, …)
        Svc->>Emb: encode_batch([art.text_paraphrased for art in articles])
        Emb-->>Svc: list of 384-d embeddings
        Svc->>DRepo: save(LegalDocument(...))
        loop For each article
            Svc->>CRepo: save(LegalChunk(... embedding=...))
        end
    end
    Svc->>VRepo: save(CorpusVersion(version, laws_count, articles_count, chunks_count, manifest, is_active=False))
    Svc->>PG: COMMIT
    Svc-->>Cmd: IngestionReport
    Cmd-->>Op: print summary (152 chunks, 9 laws, 0 warnings)
```

### Failure path (atomic rollback)

```mermaid
sequenceDiagram
    participant Svc as CorpusIngestionService
    participant Parser as MarkdownCorpusParser
    participant PG as Postgres

    Svc->>PG: BEGIN
    Svc->>Parser: parse_file(file)
    Parser-->>Svc: raises ParseError on a malformed file
    Svc->>PG: ROLLBACK
    Svc-->>Svc: re-raise with file path + line number in error message
```

---

## Flow: US-02 Build embeddings

```mermaid
sequenceDiagram
    participant Svc as CorpusIngestionService
    participant Emb as EmbeddingModel

    Svc->>Emb: encode_batch(texts, batch_size=32)
    Emb->>Emb: tokenize
    Emb->>Emb: forward pass through model
    Emb->>Emb: mean-pool + L2-normalize
    Emb-->>Svc: list[list[float]] each of length 384
    Svc->>Svc: assert len(emb) == 384 and abs(np.linalg.norm(emb) - 1.0) < 1e-3
```

`EmbeddingModel` is wrapped so the underlying `SentenceTransformer` is a singleton lazy-loaded on first call; CPU is the default device.

---

## Flow: US-03 F4 retrieves legal basis

### Semantic path

```mermaid
sequenceDiagram
    participant F4 as F4 service
    participant Svc as LegalCitationService
    participant Hybrid as HybridMatcher
    participant Emb as EmbeddingModel
    participant CRepo as LegalChunkRepository
    participant LogRepo as RagQueryLogRepository
    participant PG as Postgres

    F4->>Svc: retrieve_legal_basis(finding_text, corpus_version="2026-05-10", top_k=3, threshold=0.65, prefer_anchors=criterion.legal_anchor, criterion_id="B7", analysis_id=A)
    Svc->>Hybrid: find_exact_anchor(finding_text, "2026-05-10")
    Hybrid-->>Svc: None
    Svc->>Emb: encode(finding_text)
    Emb-->>Svc: q  (384-d, normalized)
    Svc->>CRepo: cosine_search(version, q, top_k=3, threshold=0.65, prefer_anchors=["art-12-lpc"])
    CRepo->>PG: SELECT ..., embedding <=> %s AS distance ORDER BY distance LIMIT 3 (with anchor filter first; if 0, broaden)
    PG-->>CRepo: rows with similarity = 1 - distance
    CRepo-->>Svc: list[LegalChunk]
    Svc->>Svc: build LegalReference list (join LegalDocument for law_title)
    Svc->>LogRepo: log_rag_query(query_text_hash=sha256(salt+finding_text), top_score, results_count_above_threshold, criterion_id, analysis_id)
    Svc-->>F4: list[LegalReference]
```

### Hybrid (exact) path

```mermaid
sequenceDiagram
    participant F4 as F4 service
    participant Svc as LegalCitationService
    participant Hybrid as HybridMatcher
    participant CRepo as LegalChunkRepository

    F4->>Svc: retrieve_legal_basis("La cláusula 6.2 contradice el Art. 12 LPC ...", "2026-05-10", ...)
    Svc->>Hybrid: find_exact_anchor(text, "2026-05-10")
    Hybrid->>Hybrid: regex art\\.?\\s*12\\s*lpc → (law_id="ley-proteccion-consumidor", anchor="art-12")
    Hybrid->>CRepo: get_by_anchor("ley-proteccion-consumidor", "art-12", "2026-05-10")
    CRepo-->>Hybrid: LegalChunk
    Hybrid-->>Svc: LegalReference(similarity_score=1.0)
    Svc-->>F4: [LegalReference]
```

### Empty result

```mermaid
sequenceDiagram
    participant F4 as F4 service
    participant Svc as LegalCitationService

    F4->>Svc: retrieve_legal_basis(generic_text, ...)
    Svc->>Svc: best similarity = 0.55 < threshold 0.65
    Svc-->>F4: []  (empty list)
    Note over F4: F4 emits the finding with legal_basis=[] tagged market_based or unverifiable_legal
```

---

## Flow: US-04 Cite-or-stay-silent enforcement

```mermaid
sequenceDiagram
    participant Svc as LegalCitationService
    participant CRepo as LegalChunkRepository
    participant LogRepo as RagQueryLogRepository

    Svc->>CRepo: cosine_search(...) returns [{score:0.58},{score:0.42}]
    CRepo-->>Svc: candidates
    Svc->>Svc: filter by threshold 0.65 → []
    Svc->>LogRepo: log_rag_query(results_count_total=2, results_count_above_threshold=0, top_score=0.58)
    Svc-->>Svc: return []
```

---

## Flow: US-05 Versioning

When F4 needs to regenerate an old report, F6 calls `LegalCitationService.get_chunk_by_anchor(law_id, anchor, corpus_version=analysis.corpus_version)`. The retrieval is always pinned to the analysis's stored version.

```mermaid
sequenceDiagram
    participant F6 as F6 report generator
    participant Svc as LegalCitationService
    participant CRepo as LegalChunkRepository

    F6->>Svc: get_chunk_by_anchor("codigo-civil", "art-1605", analysis.corpus_version)
    Svc->>CRepo: get_by_anchor("codigo-civil", "art-1605", "2026-05-10")
    CRepo-->>Svc: LegalChunk
    Svc-->>F6: LegalReference for "see verbatim" button
```

---

## Flow: US-06 Operator audits corpus

```mermaid
sequenceDiagram
    actor Op as Operator
    participant Cmd as CorpusAuditCommand
    participant Svc as CorpusIngestionService
    participant VRepo as CorpusVersionRepository
    participant DRepo as LegalDocumentRepository
    participant CRepo as LegalChunkRepository
    participant LogRepo as RagQueryLogRepository

    Op->>Cmd: python manage.py corpus_audit --version latest_active --export report.csv
    Cmd->>Svc: audit(version)
    Svc->>VRepo: get_active()
    VRepo-->>Svc: CorpusVersion
    Svc->>DRepo: list_by_version(v)
    Svc->>CRepo: top_cited(v, since=30d)
    Svc->>LogRepo: empty_query_count_by_criterion(v, since=30d)
    Svc->>DRepo: list_overdue_verification(threshold=6 months)
    Svc-->>Cmd: AuditReport
    Cmd-->>Op: print + write CSV
```

---

## Class Diagram

```mermaid
classDiagram
    class CorpusIngestionService
    class LegalCitationService
    class MarkdownCorpusParser
    class EmbeddingModel
    class HybridMatcher
    class CorpusVersionRepository
    class LegalDocumentRepository
    class LegalChunkRepository
    class RagQueryLogRepository
    class CorpusIngestCommand
    class CorpusActivateCommand
    class CorpusAuditCommand
    class CorpusQueryCommand
    class InternalRagQueryView

    CorpusIngestionService *-- MarkdownCorpusParser
    CorpusIngestionService *-- EmbeddingModel
    CorpusIngestionService o-- CorpusVersionRepository
    CorpusIngestionService o-- LegalDocumentRepository
    CorpusIngestionService o-- LegalChunkRepository
    LegalCitationService *-- EmbeddingModel
    LegalCitationService *-- HybridMatcher
    LegalCitationService o-- LegalChunkRepository
    LegalCitationService o-- RagQueryLogRepository
    CorpusIngestCommand ..> CorpusIngestionService
    CorpusActivateCommand ..> CorpusIngestionService
    CorpusAuditCommand ..> CorpusIngestionService
    InternalRagQueryView ..> LegalCitationService
```

---

## Notes

- The `EmbeddingModel` adapter is a thin wrapper around `sentence_transformers.SentenceTransformer`. The model object is held at module scope and lazily constructed; multiple threads share it (the underlying torch model is thread-safe for inference).
- The `HybridMatcher` uses a list of compiled regexes from PRD §6.2. New regexes are added when new laws are absorbed.
- `LegalCitationService.retrieve_legal_basis` is **synchronous** (Django ORM + local model) and fast (sub-150 ms P95). It is called from F4's Celery task in the worker process.

**End of document.**
