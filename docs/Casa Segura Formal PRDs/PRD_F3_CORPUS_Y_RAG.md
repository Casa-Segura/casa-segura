# PRD: F3 — Legal Corpus & Citation Retrieval (RAG)

**Version:** 1.0
**Status:** Approved for development
**Author:** Product Team
**Date:** 2026-05-10
**Depends on:** F8 (database schema base)
**Blocks:** F4 (Rubric Engine), F6 (Report Generation)

---

## 1. Problem Statement

Casa Segura's differentiator is that every report finding is backed by a verbatim citation from a specific Salvadoran law. This turns a subjective verdict into an auditable statement, gives the user vocabulary to negotiate with the seller, and reduces the product's legal risk because we are not opining on the contract but reporting what the law says.

The feature must serve two consumers: F4 (Rubric Engine), which needs to find the correct law to anchor a finding as it evaluates each criterion, and F6 (Report Generation), which needs to serve the paraphrase and the official reference to display to the user. Product discipline is strict: if there is no article with sufficient relevance, the finding is emitted without citation and labeled `market_based` or `unverifiable`. Nothing is invented. A distant article is never "forced" to fit. That discipline is what makes it defensible to show law articles without a law-practice license.

Additionally, the feature is responsible for keeping the corpus updated, versioned, and reproducible. A six-month-old legal citation must be regeneratable identically even if the law has been reformed in the meantime. That is why the corpus is versioned as an immutable set and each analysis records the version it used.

---

## 2. Scope

**In scope:**

- Maintenance of the legal corpus in structured markdown files with YAML frontmatter
- Corpus ingestion into the database: parsing, per-article chunking, embedding generation, persistence
- Versioning of the full corpus (`CorpusVersion`) with a manifest of included laws
- Vector indexing with pgvector (HNSW or IVF depending on size)
- Internal retrieval API: given a finding text, returns the top-K most relevant `LegalChunk` items with score
- "Cite or stay silent" discipline: filter results below a configurable similarity threshold
- Filtering by tags and finding categories to improve precision
- Hybrid-search support: vector + exact text when the finding explicitly cites an article
- Safe re-ingestion: updating the corpus creates a new version without affecting existing analyses
- Manual curation of the corpus via PR process on the markdown files
- Usage metrics: which articles are cited most, which findings remain uncited

**Out of scope:**

- Automatically generating paraphrases from law verbatim text (the paraphrase is curated human work)
- Maintaining the legal corpus of other countries (only El Salvador)
- Legal analysis of corpus content (curation is human legal responsibility)
- Automatic detection of legal reforms (a human process monitors official sources)
- Hosting the law repository (markdown files live in the project repo)
- Admin UI for editing the corpus via UI (it is edited in files)
- Citations to doctrine, case law, or secondary regulation (only laws in force)
- Multi-language corpus support (Spanish only)

---

## 3. User Stories

### US-01: System ingests a corpus version

**As an** operator,
**I want to** ingest a specific version of the legal corpus from markdown files,
**So that** the laws are available for retrieval.

**Acceptance criteria:**

- The command `ingest-corpus --version <version>` reads `.md` files from `corpus/laws/`
- Each file must have valid YAML frontmatter with the required fields from DOMAIN_MODEL §3.5
- The system parses each file, identifies article sections by `### Art. N` headings, and creates a `LegalChunk` per article
- The command is idempotent: if the version already exists, it fails with explicit error; the operator must use `--force` to overwrite
- A `CorpusVersion` is atomically created when all chunks of all laws are inserted without error
- If ingestion fails partially, full rollback occurs (single transaction)
- The `embedding` of each chunk is generated using the configured model (`paraphrase-multilingual-MiniLM-L12-v2`)
- The version manifest is computed: list of laws with their IDs, counts, and content hash
- The command produces an ingestion report: chunks created, parse errors, warnings about empty or malformed chunks

**Expected structure of a law file:**

```markdown
---
law_id: ley-inquilinato
title: Ley de Inquilinato
short_title: Inquilinato
decree: "D.L. 2591"
issued_at: 1958-02-14
official_gazette: "Nº 35, T. 178, 20-02-1958"
status: in_force_with_amendments
subject: lease
source_url: "https://..."
last_verified: 2026-05-10
relevance_to_casa_segura: high
covers:
  - residential lease
  - tenement houses
  - termination causes
tags: [lease, residential, tenant]
---

# Ley de Inquilinato

[optional descriptive content]

### Art. 2
Los derechos concedidos al inquilino por esta ley son irrenunciables...

**Tags:** non_waivable, void_clause

**Severity:** override_critical

**Relevant_for:** [E1, A1]

### Art. 4
Todo contrato de arrendamiento o subarrendamiento sujeto a esta ley...
```

---

### US-02: System builds and stores chunk embeddings

**As the** system,
**I want to** generate vector embeddings for each corpus chunk,
**So that** semantic queries work.

**Acceptance criteria:**

- The system uses the `paraphrase-multilingual-MiniLM-L12-v2` model from Sentence Transformers
- Embedding dimensions are 384
- The system embeds the chunk's `text_paraphrased` field, NOT the verbatim (the verbatim is for display; the paraphrase is for search)
- Embeddings are persisted in the `embedding` column of pgvector type `vector(384)`
- An HNSW index is created over `embedding` with parameters `m=16, ef_construction=64`
- If the model is not available locally, it is downloaded the first time to the directory configured in `EMBEDDING_MODEL_CACHE_DIR`
- The system validates that produced embeddings have norm close to 1 (sentence-transformers models normalize by default)
- For chunks with very long text (> 512 tokens), they are truncated to the first 512 tokens of the paraphrase

**Configuration:**

- `EMBEDDING_MODEL_NAME` env var (default `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`)
- `EMBEDDING_DIMENSIONS` env var (default 384)
- `EMBEDDING_MODEL_CACHE_DIR` env var (default `/var/cache/casa-segura/models`)
- `EMBEDDING_DEVICE` env var (default `cpu`; `cuda` if GPU available)
- `EMBEDDING_BATCH_SIZE` env var (default 32)

---

### US-03: F4 queries relevant articles for a finding

**As** F4 (Rubric Engine),
**I want to** receive corpus articles relevant to a finding I am evaluating,
**So that** I can anchor the finding to the correct legal citation.

**Acceptance criteria:**

- F3 exposes a function `retrieve_legal_basis(finding_text, options)` callable from F4
- Parameters: `finding_text` (text of the finding to anchor), `corpus_version` (version to use), `top_k` (default 5), `threshold` (default 0.65), `filter_tags` (optional), `filter_law_ids` (optional)
- The function computes the embedding of `finding_text` with the same model
- It runs a cosine-similarity search against the chunks of the requested version
- Returns a list sorted by descending similarity, filtered by threshold
- Each result contains: `chunk_id`, `law_id`, `article_number`, `anchor`, `text_paraphrased`, `similarity_score`, and the `LegalReference` object ready to embed in a `Finding`
- If after threshold filtering there are no results, it returns an empty list
- The function NEVER invents, completes, or "adjusts" results; what it returns are real chunks from the corpus

**Hybrid search (when applicable):**

- If `finding_text` explicitly cites an article (e.g. "Art. 1605 CC" or "Art. 4 Ley de Inquilinato"), the system:
  1. First tries exact lookup by `(law_id, article_number)`
  2. If an exact match is found, returns it with score = 1.0 even if semantic search would have returned a different chunk
  3. If no exact match, falls back to semantic search
- Patterns recognized for exact search are defined in §6.2

**Example usage from F4:**

```python
# F4 evaluating criterion B2 (interest rate on total balance)
finding_text = "The contract states that interest is calculated on the outstanding total balance, not on outstanding principal."

results = f3.retrieve_legal_basis(
    finding_text=finding_text,
    corpus_version=current_corpus_version,
    top_k=3,
    threshold=0.65,
    filter_tags=["interest", "consumer"]
)

# results[0] would be the Art. 12 LPC chunk with score ~0.88
# results[1] could be Art. 19 LPC with score ~0.72
# results[2] could not exist if nothing else passes the threshold
```

---

### US-04: System applies cite-or-stay-silent discipline

**As the** system,
**I want to** guarantee that I only emit citations with verified relevance,
**So that** report findings are defensible and never invented.

**Acceptance criteria:**

- The similarity threshold is strict: 0.65 by default, configurable per consumer
- Results with similarity below the threshold are discarded, not returned
- F3 NEVER takes "whatever is closest" when all are below threshold
- If the result list ends empty, F4 emits the finding with `legal_basis: []` and labels it `market_based` or `unverifiable` per the criterion's context
- The LLM in F4 is NOT permitted to "infer" an article when F3 found none; F4's prompt explicitly tells it to use only what F3 hands it
- For criteria with explicit `legal_anchor` (defined in `Criterion.legal_anchor`), F3 prioritizes those articles in the search as an initial filter
- Each query is logged with: `finding_text` (hash, not content), `top_k`, `threshold`, `results_count`, `results_above_threshold`, for quality analysis

**RAG quality metrics:**

- Findings-with-citation rate: % of F4-emitted findings ending with at least one `legal_basis`
- Findings-without-citation rate: % ending with `legal_basis: []`
- Top-1 citation rate: % of findings where the first result has score > 0.80
- Score distribution: histogram of first-result scores per query

---

### US-05: System versions the corpus

**As an** operator,
**I want to** have each analysis use a specific reproducible corpus version,
**So that** a report regenerated months later produces exactly the same citations.

**Acceptance criteria:**

- Each `CorpusVersion` is identified by a unique tag (e.g. `2026-05-10` or `1.2.0`)
- A version, once created, is immutable: chunks cannot be added, modified, or deleted
- If the corpus needs to change, a new full version is created
- F4 always invokes F3 with a specific `corpus_version`, typically the `latest_active` configured in the system
- `ContractAnalysis.corpus_version` records the version used in each analysis
- F6 (report regeneration) uses the version stored in the analysis, not necessarily the current one
- The system maintains a `latest_active` alias pointing to the version in force for new analyses
- Changing the `latest_active` alias requires an explicit command and records an event in the audit log
- Old versions are kept indefinitely (no chunk from a past version is deleted)

---

### US-06: Operator audits corpus coverage

**As an** operator,
**I want to** know which laws are covered, which articles are missing, and which findings most often end without citation,
**So that** I can prioritize curation.

**Acceptance criteria:**

- Command `audit-corpus` produces a report with:
  - Laws included in `latest_active` with article counts
  - List of laws pending incorporation (declared as TODO in the repo)
  - Most-cited chunks in the last month
  - Findings most frequently left uncited (based on F3 logs)
  - Chunks with inconsistent or empty tags
  - Chunks whose `last_verified` is overdue (over 6 months)
- The report is printed to stdout and optionally exported to CSV
- The operator uses this report to decide which corpus to expand or re-curate

---

## 4. Business Rules

**BR-01:** The "cite or stay silent" discipline is invariant. F3 never returns results below the similarity threshold, no matter how many there are. F4 never emits citations without F3 returning them.

**BR-02:** Embeddings are computed over the paraphrase (`text_paraphrased`), not the verbatim. The paraphrase is optimized to semantically match common findings; the verbatim preserves formal legal language.

**BR-03:** A `CorpusVersion` is immutable. Any change in the corpus requires creating a new full version. This guarantees reproducibility of past analyses.

**BR-04:** Corpus paraphrases are human-curated and verified against the official source. The system does not generate paraphrases automatically. Errors in a paraphrase are corrected by creating a new corpus version.

**BR-05:** `text_verbatim` is optional in a chunk but recommended. When present, F6 may display it to the user as "see article verbatim text" in the report. When absent, F6 only shows the paraphrase.

**BR-06:** The default similarity threshold is 0.65. It is configurable per call but the default is not lowered without justification. Lowering it increases recall but degrades precision, contradicting product discipline.

**BR-07:** For criteria with explicit `legal_anchor` (defined in `Criterion`), F3 uses the anchor as an initial search filter. This guarantees that a criterion known to anchor on Art. 1605 CC always searches that article first before exploring others.

**BR-08:** Chunk tags are normalized (lowercase, no accents, no special characters) both in the corpus and in filter queries.

**BR-09:** If the embedding model changes in a future version, the full corpus must be re-ingested (embeddings from the old and new models are not comparable). The previous corpus version remains accessible for historical reports.

**BR-10:** The corpus in markdown files is the single source of truth. The database is only a query index. If the DB is corrupted, it is rebuilt by ingesting from the files.

**BR-11:** Chunks may have `severity_hint` (e.g. `override_critical`, `red`, `yellow`). This is corpus information that F4 uses to calibrate finding weight, but is not binding: F4 may contradict the hint if contract evidence points to a different severity.

**BR-12:** The RAG usage log (what was cited when, what was left uncited) is persisted in a `rag_query_log` table with TTL of 90 days. Allows analyzing usage patterns and improving the corpus, but does not store finding text.

---

## 5. Data Models

### 5.1 LegalDocument

```sql
CREATE TABLE legal_document (
    law_id TEXT NOT NULL,
    corpus_version TEXT NOT NULL,

    title TEXT NOT NULL,
    short_title TEXT,
    decree TEXT,
    issued_at DATE,
    official_gazette TEXT,
    status TEXT NOT NULL CHECK (status IN ('in_force', 'repealed', 'in_force_with_amendments')),
    subject TEXT,
    source_url TEXT,
    last_verified DATE NOT NULL,
    relevance_to_casa_segura TEXT CHECK (relevance_to_casa_segura IN ('high', 'medium', 'low')),
    covers TEXT[],
    tags TEXT[],

    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (law_id, corpus_version)
);

CREATE INDEX idx_legal_document_corpus_version ON legal_document(corpus_version);
CREATE INDEX idx_legal_document_status ON legal_document(status);
```

### 5.2 LegalChunk

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE legal_chunk (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_version TEXT NOT NULL,
    law_id TEXT NOT NULL,
    article_number TEXT NOT NULL,
    anchor TEXT NOT NULL,

    text_paraphrased TEXT NOT NULL,
    text_verbatim TEXT,

    embedding VECTOR(384) NOT NULL,

    tags TEXT[] NOT NULL DEFAULT '{}',
    relevance_for_findings TEXT[] NOT NULL DEFAULT '{}',
    severity_hint TEXT CHECK (severity_hint IN ('override_critical', 'red', 'yellow', 'green', NULL)),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    FOREIGN KEY (law_id, corpus_version) REFERENCES legal_document(law_id, corpus_version) ON DELETE CASCADE,
    UNIQUE (corpus_version, law_id, anchor)
);

CREATE INDEX idx_legal_chunk_corpus_version ON legal_chunk(corpus_version);
CREATE INDEX idx_legal_chunk_law_id ON legal_chunk(law_id);
CREATE INDEX idx_legal_chunk_tags ON legal_chunk USING GIN(tags);
CREATE INDEX idx_legal_chunk_relevance ON legal_chunk USING GIN(relevance_for_findings);

-- HNSW index for vector search
CREATE INDEX idx_legal_chunk_embedding ON legal_chunk
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

### 5.3 CorpusVersion

```sql
CREATE TABLE corpus_version (
    version TEXT PRIMARY KEY,
    released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    laws_count INTEGER NOT NULL,
    articles_count INTEGER NOT NULL,
    chunks_count INTEGER NOT NULL,
    manifest JSONB NOT NULL,

    changelog TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Only one version can be active at a time
CREATE UNIQUE INDEX idx_corpus_version_active ON corpus_version(is_active) WHERE is_active = TRUE;
```

### 5.4 RagQueryLog (observability)

```sql
CREATE TABLE rag_query_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID,
    criterion_id TEXT,

    query_text_hash TEXT NOT NULL,
    corpus_version TEXT NOT NULL,
    top_k INTEGER NOT NULL,
    threshold NUMERIC(3,2) NOT NULL,
    filter_tags TEXT[],
    filter_law_ids TEXT[],

    results_count_total INTEGER NOT NULL,
    results_count_above_threshold INTEGER NOT NULL,
    top_score NUMERIC(4,3),

    queried_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '90 days')
);

CREATE INDEX idx_rag_query_log_analysis ON rag_query_log(analysis_id);
CREATE INDEX idx_rag_query_log_expires ON rag_query_log(expires_at);
CREATE INDEX idx_rag_query_log_criterion ON rag_query_log(criterion_id);
```

---

## 6. Integration Points

### 6.1 Consumed by F4 (Rubric Engine)

F3 exposes an internal Python function (not HTTP) consumed from the same process or via internal queue.

```python
class LegalCitationService:
    def retrieve_legal_basis(
        self,
        finding_text: str,
        corpus_version: str,
        top_k: int = 5,
        threshold: float = 0.65,
        filter_tags: list[str] | None = None,
        filter_law_ids: list[str] | None = None,
        prefer_anchors: list[str] | None = None,
    ) -> list[LegalReference]:
        ...

    def get_chunk_by_anchor(
        self,
        law_id: str,
        anchor: str,
        corpus_version: str,
    ) -> LegalReference | None:
        ...
```

### 6.2 Recognized exact-citation patterns

For hybrid search, F3 recognizes explicit patterns in the finding text and resolves them to exact search before falling back to semantic.

Regex patterns (case-insensitive):

```
art\.?\s*(\d+)\s*(?:-?[a-z])?\s*c\.?c\.?              → Código Civil
art\.?\s*(\d+)\s*(?:-?[a-z])?\s*lpc                   → Ley de Protección al Consumidor
art\.?\s*(\d+)\s*(?:-?[a-z])?\s*(?:ley\s*de\s*)?inquilinato  → Ley de Inquilinato
art\.?\s*(\d+)\s*(?:-?[a-z])?\s*ivu                   → Ley sobre Contratos del IVU
art\.?\s*(\d+)\s*(?:-?[a-z])?\s*fsv                   → Ley del FSV
art\.?\s*(\d+)\s*(?:-?[a-z])?\s*l(?:af|f)             → Ley de Arrendamiento Financiero
art\.?\s*(\d+)\s*(?:-?[a-z])?\s*l\.?u\.?c\.?         → Ley de Urbanismo y Construcción
```

### 6.3 External dependencies

| Dependency | Version | Use |
|---|---|---|
| `pgvector` | ≥ 0.7 | Postgres extension for vector type |
| `sentence-transformers` | ≥ 2.5 | Embedding model |
| `torch` | ≥ 2.0 | Model backend |
| `pyyaml` | ≥ 6.0 | Frontmatter parsing |
| `markdown-it-py` | ≥ 3.0 | Markdown content parsing |

### 6.4 Corpus repository structure

```
corpus/
├── README.md                          # Corpus documentation
├── manifest.yaml                       # Current version definition
├── versions/                           # Published version history
│   ├── 2026-05-10/
│   │   └── manifest.json
│   └── 2026-08-01/
│       └── manifest.json
└── laws/
    ├── 01-ley-inquilinato.md
    ├── 02-ley-ivu.md
    ├── 03-ley-fsv.md
    ├── 04-ley-compras-publicas.md
    ├── 05-ley-arrendamiento-financiero.md
    ├── 06-ley-lotificaciones.md         # pending
    ├── 07-ley-urbanismo-construccion.md
    ├── 08-codigo-civil-extracto.md
    └── 09-ley-proteccion-consumidor.md
```

### 6.5 Operations command

```bash
# Ingest a new version
casa-segura corpus ingest --version 2026-05-10 --path ./corpus/laws

# Activate a version
casa-segura corpus activate --version 2026-05-10

# Audit coverage
casa-segura corpus audit --version latest_active

# List available versions
casa-segura corpus list

# Test a query
casa-segura corpus query --version latest_active --text "el contrato exime al vendedor de saneamiento"
```

---

## 7. API Surface

F3 does not expose public HTTP endpoints. All interaction is internal.

For QA and debugging, a protected endpoint is exposed:

### 7.1 `POST /v1/internal/rag/query` (requires `X-Internal-Auth`)

```json
{
    "finding_text": "El contrato exime al vendedor de saneamiento por evicción.",
    "corpus_version": "latest_active",
    "top_k": 5,
    "threshold": 0.65,
    "filter_tags": ["saneamiento", "vendedor"]
}
```

**Response:**

```json
{
    "corpus_version_resolved": "2026-05-10",
    "query_embedding_time_ms": 45,
    "search_time_ms": 12,
    "results": [
        {
            "chunk_id": "uuid",
            "law_id": "codigo-civil",
            "law_title": "Código Civil",
            "article": "Art. 1644",
            "anchor": "art-1644",
            "text_paraphrased": "Es nulo todo pacto en que se exima al vendedor del saneamiento de evicción, siempre que en ese pacto haya habido mala fe de parte suya.",
            "text_verbatim": "Art. 1644.- Es nulo todo pacto en que...",
            "similarity_score": 0.91,
            "tags": ["saneamiento", "evicción", "compraventa"],
            "severity_hint": "override_critical"
        },
        {
            "chunk_id": "uuid",
            "law_id": "codigo-civil",
            "law_title": "Código Civil",
            "article": "Art. 1639",
            "anchor": "art-1639",
            "text_paraphrased": "La obligación de saneamiento comprende dos objetos: amparar al comprador en el dominio y posesión pacífica de la cosa vendida, y responder de los defectos ocultos.",
            "similarity_score": 0.78,
            "tags": ["saneamiento", "obligaciones", "vendedor"]
        }
    ],
    "results_count_total": 5,
    "results_count_above_threshold": 2
}
```

---

## 8. LLM Prompts

F3 does not use an LLM in its primary flow. The embedding model (sentence-transformers) is deterministic, not a generative LLM.

The only optional LLM use in F3 is for the re-ranking phase, outside the initial scope:

### 8.1 LLM re-ranker (optional, not MVP)

If precision over the top-K vector results is to be improved:

```
You are a relevance judge between a legal finding and law articles. Given a finding and a list of candidate articles, sort them by descending relevance to the finding. Do not add or remove articles; only reorder.

FINDING:
{{finding_text}}

CANDIDATE ARTICLES:
1. {{article_1}}
2. {{article_2}}
...

Return JSON: {"reranked_order": [<id_1>, <id_2>, ...]}
```

This layer does NOT enter the MVP. Pure vector search with threshold is sufficient.

---

## 9. Non-Functional Requirements

- **P50 latency for retrieve_legal_basis:** under 50 ms.
- **P95 latency for retrieve_legal_basis:** under 150 ms.
- **Throughput:** support at least 50 queries per second to sustain F4's aggregate throughput (each analysis can invoke F3 up to 38 times).
- **Findings-with-at-least-one-citation rate:** over 70% of findings F4 produces with the full corpus.
- **Top-1 precision:** the most relevant citation returned must be correct for over 85% of test cases (human evaluation against a curated set).
- **Initial full-corpus ingestion:** under 10 minutes for 200 chunks on a CPU machine.
- **Index size:** under 100 MB for 1000 chunks (estimate with HNSW + metadata).
- **Availability:** depends on Postgres; target 99.5%.
- **Observability:** Prometheus metrics for query latency, score distribution, empty-query rate, per-criterion distribution.

---

## 10. Open Questions

1. Is the 0.65 threshold correct? Requires evaluation with a set of manually labeled real findings. Possibly different per criterion: a very specific criterion (B7 - late interest on total balance) could have a higher threshold (0.75), while a more general one (E9 - abusive penalty) could need 0.55.

2. Should a finding be allowed citations from multiple laws? For example, a finding on an abusive clause could cite LPC and Civil Code simultaneously. The current structure allows it (legal_basis is a list). A policy on the maximum number of citations shown in the report (2? 3?) is needed.

3. Should queries with no results trigger an operator alert? If a criterion frequently fails to find an anchor in the corpus, that may signal a gap. Product must define the alert threshold.

4. Should the corpus include doctrine and case law, or stay strictly with laws? Doctrine broadens coverage but opens debate on which to cite (a single author, several contradictory ones). Case law is similar. Product must decide; my recommendation is no in MVP.

5. How are legal reforms that change articles handled? The current strategy is to create a new full corpus version. An alternative is to version at the chunk level (keep `art-4-v1` and `art-4-v2`). The current one is simpler but implies re-ingesting everything when one law changes.

6. Is a mechanism needed to "deprecate" a chunk that no longer applies? For example, repealed articles (Chapter V of Ley de Inquilinato). They are currently included with a note; they could be filtered automatically from search.

7. Does human curation of the corpus have a formal process? Who reviews a paraphrase before commit? Without a gatekeeper, quality may degrade. Product must define the process (peer review in PRs, lawyer reviewer, etc.).

8. Can paraphrases be updated to improve recall, or are they immutable once published? Updating paraphrases changes the embeddings, requires full re-ingestion, and creates a new version. Is the effort worth a marginal gain?

---

**End of document.**
