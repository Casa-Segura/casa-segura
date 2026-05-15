# Solution Diagrams — F3: Legal Corpus & Citation Retrieval

> Generated: 2026-05-15

---

## 1. Class Diagram (UML)

### 1.1 Domain + Application

```mermaid
classDiagram
    class CorpusVersion {
        <<Pydantic>>
        +str version
        +datetime released_at
        +int laws_count
        +int articles_count
        +int chunks_count
        +dict manifest
        +str|None changelog
        +bool is_active
    }
    class LegalDocument {
        <<Pydantic>>
        +str law_id
        +str corpus_version
        +str title
        +str|None short_title
        +str|None decree
        +date|None issued_at
        +str status
        +date last_verified
        +list~str~ tags
        +str file_path
        +str content_hash
    }
    class LegalChunk {
        <<Pydantic>>
        +UUID|None id
        +str corpus_version
        +str law_id
        +str article_number
        +str anchor
        +str text_paraphrased
        +str|None text_verbatim
        +list~float~ embedding
        +list~str~ tags
        +list~str~ relevance_for_findings
        +str|None severity_hint
    }
    class LegalReference {
        <<Pydantic>>
        +UUID chunk_id
        +str law_id
        +str law_title
        +str article
        +str anchor
        +str text_paraphrased
        +str|None text_verbatim
        +float similarity_score
        +list~str~ tags
        +str|None severity_hint
        +str|None official_source
        +str corpus_version
    }
    class RagQueryLog {
        <<Pydantic>>
        +UUID|None id
        +UUID|None analysis_id
        +str|None criterion_id
        +str query_text_hash
        +str corpus_version
        +int top_k
        +float threshold
        +int results_count_total
        +int results_count_above_threshold
        +float|None top_score
        +datetime queried_at
    }
    class IngestCorpusVersion {
        <<Command>>
        +str version
        +Path path
        +bool force
    }
    class ActivateCorpusVersion {
        <<Command>>
        +str version
    }
    class CreateLegalDocument {
        <<Command>>
        +LegalDocument doc
    }
    class CreateLegalChunk {
        <<Command>>
        +LegalChunk chunk
    }
    class CreateCorpusVersion {
        <<Command>>
        +CorpusVersion version
    }
    class LogRagQuery {
        <<Command>>
        +RagQueryLog entry
    }
    class GetActiveCorpusVersion {
        <<Query>>
    }
    class GetChunkByAnchor {
        <<Query>>
        +str law_id
        +str anchor
        +str corpus_version
    }
    class SearchChunks {
        <<Query>>
        +str corpus_version
        +list~float~ embedding
        +int top_k
        +float threshold
        +list~str~|None filter_tags
        +list~str~|None filter_law_ids
        +list~str~|None prefer_anchors
    }
    class corpus_handlers {
        <<handlers>>
        +ingest_version(cmd, ...) IngestionReport
        +activate_version(cmd, repo) CorpusVersion
        +create_legal_document(cmd, repo) LegalDocument
        +create_legal_chunk(cmd, repo) LegalChunk
        +log_rag_query(cmd, repo) RagQueryLog
    }
    class corpus_queries_handlers {
        <<handlers>>
        +get_active_version(query, repo) CorpusVersion|None
        +get_chunk_by_anchor(query, repo) LegalChunk|None
        +search_chunks(query, repo) list~LegalChunk~
    }
    class CorpusIngestionService {
        -CorpusVersionRepository version_repo
        -LegalDocumentRepository doc_repo
        -LegalChunkRepository chunk_repo
        -EmbeddingModel embedder
        -MarkdownCorpusParser parser
        +ingest(version, path, force) IngestionReport
        +activate(version) None
        +audit(version) AuditReport
    }
    class LegalCitationService {
        -LegalChunkRepository chunk_repo
        -EmbeddingModel embedder
        -RagQueryLogRepository log_repo
        -HybridMatcher hybrid
        +retrieve_legal_basis(text, version, top_k, threshold, filter_tags, prefer_anchors, criterion_id, analysis_id) list~LegalReference~
        +get_chunk_by_anchor(law_id, anchor, version) LegalReference|None
    }
    class HybridMatcher {
        +find_exact_anchor(text, version) LegalReference|None
        -ARTICLE_PATTERNS list~Regex~
    }
    class EmbeddingModel {
        <<adapter for SentenceTransformer>>
        +encode(text) list~float~
        +encode_batch(texts) list~list~float~~
        +dim int
    }
    class MarkdownCorpusParser {
        +parse_file(path) ParsedDocument
        +split_articles(body) list~ParsedArticle~
        +normalize_tags(tags) list~str~
    }
    LegalReference o-- LegalChunk : built from
    corpus_handlers ..> IngestCorpusVersion
    corpus_handlers ..> ActivateCorpusVersion
    CorpusIngestionService *-- MarkdownCorpusParser
    CorpusIngestionService *-- EmbeddingModel
    LegalCitationService *-- EmbeddingModel
    LegalCitationService *-- HybridMatcher
```

### 1.2 Infrastructure

```mermaid
classDiagram
    class CorpusVersionModel {
        <<Django Model>>
    }
    class LegalDocumentModel {
        <<Django Model>>
    }
    class LegalChunkModel {
        <<Django Model>>
        +VectorField(384) embedding
    }
    class RagQueryLogModel {
        <<Django Model>>
    }
    class CorpusVersionRepository {
        <<DjangoFullRepository>>
        +get_active() CorpusVersion|None
        +mark_active(version) None
    }
    class LegalDocumentRepository {
        <<DjangoFullRepository>>
    }
    class LegalChunkRepository {
        <<DjangoFullRepository>>
        +cosine_search(version, embedding, top_k, threshold, filter_tags, prefer_anchors) list~LegalChunk~
        +get_by_anchor(law_id, anchor, version) LegalChunk|None
    }
    class RagQueryLogRepository {
        <<DjangoFullRepository>>
    }
    class CorpusIngestCommand {
        <<Django management command>>
        +handle(version, path, force) None
    }
    class CorpusActivateCommand {
        <<Django management command>>
    }
    class CorpusAuditCommand {
        <<Django management command>>
    }
    class InternalRagQueryView {
        <<DRF APIView>>
        +post(request) Response
    }
    LegalChunkRepository ..> LegalChunkModel
    CorpusIngestCommand ..> CorpusIngestionService
    InternalRagQueryView ..> LegalCitationService
```

---

## 2. Sequence Diagrams

### 2.1 Corpus ingestion

```mermaid
sequenceDiagram
    actor Op as Operator
    participant Cmd as CorpusIngestCommand
    participant Svc as CorpusIngestionService
    participant Parser as MarkdownCorpusParser
    participant Emb as EmbeddingModel
    participant DB as Postgres (tx)

    Op->>Cmd: python manage.py corpus_ingest --version 2026-05-10 --path ./corpus/laws
    Cmd->>Svc: ingest(version, path)
    Svc->>Svc: check version not already in DB (unless --force)
    loop For each .md file
        Svc->>Parser: parse_file(path)
        Parser-->>Svc: ParsedDocument(frontmatter, articles[])
        Svc->>Emb: encode_batch([article.text_paraphrased for article in articles])
        Emb-->>Svc: list of 384-d vectors
        Svc->>DB: BEGIN (if first file)
        Svc->>DB: INSERT legal_document(law_id, corpus_version, ...)
        Svc->>DB: INSERT legal_chunk x N (with embedding)
    end
    Svc->>DB: INSERT corpus_version(version, laws_count, ..., is_active=false)
    Svc->>DB: COMMIT
    Svc-->>Cmd: IngestionReport(chunks_created=152, errors=[], warnings=[])
    Cmd-->>Op: print report
```

### 2.2 Activation

```mermaid
sequenceDiagram
    actor Op as Operator
    participant Cmd as CorpusActivateCommand
    participant Repo as CorpusVersionRepository
    participant DB as Postgres

    Op->>Cmd: python manage.py corpus_activate --version 2026-05-10
    Cmd->>Repo: mark_active("2026-05-10")
    Repo->>DB: BEGIN
    Repo->>DB: UPDATE corpus_version SET is_active=FALSE WHERE is_active=TRUE
    Repo->>DB: UPDATE corpus_version SET is_active=TRUE WHERE version=$1
    Repo->>DB: COMMIT
    Repo-->>Cmd: ok
    Cmd-->>Op: print "Activated 2026-05-10"
```

### 2.3 Retrieval (semantic)

```mermaid
sequenceDiagram
    participant F4 as F4 service
    participant Svc as LegalCitationService
    participant Hybrid as HybridMatcher
    participant Emb as EmbeddingModel
    participant Repo as LegalChunkRepository
    participant DB as Postgres + HNSW
    participant Log as RagQueryLogRepository

    F4->>Svc: retrieve_legal_basis(text, version, top_k=3, threshold=0.65, prefer_anchors=["art-1605-cc"], criterion_id="A1", analysis_id=A)
    Svc->>Hybrid: find_exact_anchor(text, version)
    Hybrid-->>Svc: None (no regex match in this case)
    Svc->>Emb: encode(text)
    Emb-->>Svc: 384-d vector q
    Svc->>Repo: cosine_search(version, q, top_k=3, threshold=0.65, prefer_anchors=["art-1605-cc"])
    Repo->>DB: SELECT ... ORDER BY embedding <=> q LIMIT 3 (with anchor filter first)
    DB-->>Repo: list of (LegalChunkModel, similarity)
    Repo-->>Svc: list[LegalChunk] (sorted)
    Svc->>Svc: build LegalReference list (with law title from joined LegalDocument)
    Svc->>Log: log_rag_query(... query_text_hash, top_score, results_count_above_threshold)
    Svc-->>F4: list[LegalReference] (may be empty)
```

### 2.4 Retrieval (hybrid — exact match)

```mermaid
sequenceDiagram
    participant F4 as F4 service
    participant Svc as LegalCitationService
    participant Hybrid as HybridMatcher
    participant Repo as LegalChunkRepository

    F4->>Svc: retrieve_legal_basis("Art. 1605 CC says ...", version, ...)
    Svc->>Hybrid: find_exact_anchor(text, version)
    Hybrid->>Hybrid: regex match art\.?\s*1605\s*c\.?c\.?  → law_id="codigo-civil", anchor="art-1605"
    Hybrid->>Repo: get_by_anchor("codigo-civil", "art-1605", version)
    Repo-->>Hybrid: LegalChunk
    Hybrid-->>Svc: LegalReference(similarity_score=1.0)
    Svc-->>F4: [LegalReference]
    Note over Svc: Hybrid match short-circuits; semantic search not run.
```

### 2.5 Empty result (cite-or-stay-silent)

```mermaid
sequenceDiagram
    participant F4 as F4 service
    participant Svc as LegalCitationService
    participant Repo as LegalChunkRepository

    F4->>Svc: retrieve_legal_basis("market practice about ...", ...)
    Svc->>Repo: cosine_search returns [(chunk, 0.41), (chunk, 0.38)]
    Repo-->>Svc: candidates
    Svc->>Svc: filter by threshold 0.65 → []
    Svc-->>F4: []
    Note over F4: F4 emits the finding with legal_basis=[] and tag market_based or unverifiable_legal
```

---

## 3. State Diagram — CorpusVersion lifecycle

```mermaid
stateDiagram-v2
    [*] --> draft: markdown editing (PR)
    draft --> ingested: operator runs corpus_ingest
    ingested --> active: operator runs corpus_activate
    active --> deactivated: another version is activated
    deactivated --> active: re-activate (rare; manual)
    ingested --> [*]: corpus is queryable for historical reports even when not active
```

---

## 4. Activity Diagram — Retrieve_legal_basis

```mermaid
flowchart TD
    A[Receive finding text + filters] --> B{Hybrid match by regex?}
    B -->|yes| C[Lookup chunk by law_id + anchor]
    C --> D{Found?}
    D -->|yes| E[Return single LegalReference with score 1.0]
    D -->|no| F[Encode text with embedding model]
    B -->|no| F
    F --> G{prefer_anchors set?}
    G -->|yes| H[Restrict query to chunks whose anchor IN prefer_anchors]
    G -->|no| I[Open query across all chunks of corpus_version]
    H --> J[Run HNSW cosine search top_k]
    I --> J
    J --> K[Filter by threshold]
    K --> L{Any result after filter?}
    L -->|yes| M[Build LegalReference list with law titles]
    L -->|no| N[Return empty list]
    M --> O[Log RagQueryLog]
    N --> O
    O --> P[Return]
```

---

## 5. Component Diagram

```mermaid
graph TD
    subgraph "Source of truth"
        MD[corpus/laws/*.md]
    end
    subgraph "F3 module"
        ParserSvc[MarkdownCorpusParser]
        IngestSvc[CorpusIngestionService]
        Embed[EmbeddingModel: sentence-transformers]
        CiteSvc[LegalCitationService]
        Hybrid[HybridMatcher]
        Cmds[Management commands corpus_ingest, corpus_activate, corpus_audit, corpus_query]
        InternalView[InternalRagQueryView]
    end
    subgraph "Repositories"
        VRepo[CorpusVersionRepository]
        DRepo[LegalDocumentRepository]
        CRepo[LegalChunkRepository]
        LogRepo[RagQueryLogRepository]
    end
    subgraph "Stores"
        PG[(Postgres + pgvector HNSW)]
    end
    subgraph "Consumers"
        F4[F4 rubric engine]
        F6[F6 report — for see-verbatim button]
    end
    MD --> ParserSvc --> IngestSvc
    Cmds --> IngestSvc
    IngestSvc --> Embed
    IngestSvc --> VRepo
    IngestSvc --> DRepo
    IngestSvc --> CRepo
    VRepo --> PG
    DRepo --> PG
    CRepo --> PG
    F4 --> CiteSvc
    F6 --> CiteSvc
    InternalView --> CiteSvc
    CiteSvc --> Hybrid
    CiteSvc --> Embed
    CiteSvc --> CRepo
    CiteSvc --> LogRepo
    LogRepo --> PG
```

---

## 6. Use Case Diagram

```mermaid
graph LR
    subgraph Actors
        Op[Operator]
        F4Sys[F4 Rubric Engine]
        F6Sys[F6 Report Generator]
        QA[QA engineer]
    end
    subgraph "F3 Use Cases"
        UC1((Ingest new corpus version))
        UC2((Activate a corpus version))
        UC3((Audit coverage))
        UC4((Retrieve legal basis for a finding))
        UC5((Lookup chunk by anchor for see-verbatim))
        UC6((Query corpus directly via internal endpoint))
    end
    Op --> UC1
    Op --> UC2
    Op --> UC3
    F4Sys --> UC4
    F6Sys --> UC5
    QA --> UC6
```

---

## Notes

- The HNSW index is created once via `RunSQL` in a Django migration:
  ```sql
  CREATE INDEX idx_legal_chunk_embedding ON legal_chunk
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
  ```
- `pgvector.django.VectorField(dimensions=384)` is the Django field; cosine distance via `CosineDistance(...)`.
- Each Celery worker process and Django ASGI worker loads the embedding model lazily on first use; warm-up at process start avoids first-request latency.

**End of document.**
