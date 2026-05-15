# Implementation Plan — F3: Legal Corpus & Citation Retrieval

> Generated: 2026-05-15
> Stack: Django 5.2 LTS + DRF + Postgres 15 + pgvector + sentence-transformers
> Module: `corpus/` at the project root
> Depends on: F8 schema (tables: `corpus_version`, `legal_document`, `legal_chunk`, `rag_query_log`)

---

## Directory Structure

```
corpus/
├── domain/
│   ├── entities.py             # CorpusVersion, LegalDocument, LegalChunk, LegalReference, RagQueryLog, ParsedDocument, ParsedArticle, IngestionReport, AuditReport
│   ├── enums.py                # LegalDocumentStatus, RelevanceLevel, SeverityHint
│   ├── exceptions.py           # CorpusDomainException + subclasses
│   └── protocols.py            # EmbeddingModel Protocol
├── application/
│   ├── commands.py             # IngestCorpusVersion, ActivateCorpusVersion, CreateLegalDocument, CreateLegalChunk, CreateCorpusVersion, LogRagQuery
│   ├── queries.py              # GetActiveCorpusVersion, GetChunkByAnchor, SearchChunks
│   ├── handlers/
│   │   ├── corpus_handlers.py
│   │   └── citation_handlers.py
│   └── services/
│       ├── corpus_ingestion_service.py
│       ├── legal_citation_service.py
│       └── hybrid_matcher.py
└── infrastructure/
    ├── django/
    │   ├── apps.py             # CorpusConfig
    │   ├── models.py           # CorpusVersionModel, LegalDocumentModel, LegalChunkModel, RagQueryLogModel
    │   ├── repositories.py     # CorpusVersionRepository, LegalDocumentRepository, LegalChunkRepository, RagQueryLogRepository
    │   ├── serializers.py      # InternalRagQuerySerializer, InternalRagQueryResponse
    │   ├── views.py            # InternalRagQueryView
    │   ├── urls.py
    │   ├── management/
    │   │   └── commands/
    │   │       ├── corpus_ingest.py
    │   │       ├── corpus_activate.py
    │   │       ├── corpus_list.py
    │   │       ├── corpus_query.py
    │   │       └── corpus_audit.py
    │   └── migrations/
    │       └── 0001_initial.py  # If F8 doesn't own all the corpus tables, F3 owns them here
    ├── embeddings/
    │   └── sentence_transformer_adapter.py
    └── parsing/
        ├── markdown_parser.py
        ├── article_regex.py
        └── frontmatter_validator.py
```

---

## App Configuration

```python
# corpus/infrastructure/django/apps.py
from django.apps import AppConfig

class CorpusConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "corpus.infrastructure.django"
    label = "corpus"
    verbose_name = "Casa Segura — Legal Corpus & RAG"

    def ready(self) -> None:
        from corpus.infrastructure.embeddings.sentence_transformer_adapter import warm_up_embedding_model
        # warm up only in worker / shell, not in API process during tests
        import os
        if os.getenv("CORPUS_WARMUP_ON_READY", "false").lower() == "true":
            warm_up_embedding_model()
```

`INSTALLED_APPS` includes `"corpus.infrastructure.django"`. Migrations under `corpus/infrastructure/django/migrations/`. URLs included under `/v1/internal/rag/`.

---

## Domain Entities (Pydantic)

```python
# corpus/domain/entities.py
from datetime import datetime, date
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from corpus.domain.enums import LegalDocumentStatus, RelevanceLevel, SeverityHint


class CorpusVersion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: str
    released_at: datetime
    laws_count: int
    articles_count: int
    chunks_count: int
    manifest: dict
    changelog: str | None = None
    is_active: bool = False
    created_by: str | None = None
    created_at: datetime


class LegalDocument(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    law_id: str
    corpus_version: str
    title: str
    short_title: str | None = None
    decree: str | None = None
    issued_at: date | None = None
    official_gazette: str | None = None
    status: LegalDocumentStatus
    subject: str | None = None
    source_url: str | None = None
    last_verified: date
    relevance_to_casa_segura: RelevanceLevel | None = None
    covers: list[str] = []
    tags: list[str] = []
    file_path: str
    content_hash: str
    created_at: datetime


class LegalChunk(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | None = None
    corpus_version: str
    law_id: str
    article_number: str
    anchor: str
    text_paraphrased: str
    text_verbatim: str | None = None
    embedding: list[float] = Field(min_length=384, max_length=384)
    tags: list[str] = []
    relevance_for_findings: list[str] = []
    severity_hint: SeverityHint | None = None
    created_at: datetime | None = None


class LegalReference(BaseModel):
    chunk_id: UUID
    law_id: str
    law_title: str
    article: str
    anchor: str
    text_paraphrased: str
    text_verbatim: str | None = None
    similarity_score: float = Field(ge=0.0, le=1.0)
    tags: list[str] = []
    severity_hint: SeverityHint | None = None
    official_source: str | None = None
    corpus_version: str


class ParsedArticle(BaseModel):
    article_number: str
    anchor: str
    text_paraphrased: str
    text_verbatim: str | None = None
    tags: list[str] = []
    relevance_for_findings: list[str] = []
    severity_hint: SeverityHint | None = None


class ParsedDocument(BaseModel):
    law_id: str
    title: str
    short_title: str | None
    decree: str | None
    issued_at: date | None
    status: LegalDocumentStatus
    source_url: str | None
    last_verified: date
    relevance_to_casa_segura: RelevanceLevel | None
    covers: list[str]
    tags: list[str]
    file_path: str
    content_hash: str
    articles: list[ParsedArticle]


class IngestionReport(BaseModel):
    version: str
    laws_count: int
    articles_count: int
    chunks_created: int
    parse_errors: list[str] = []
    warnings: list[str] = []
    elapsed_seconds: float


class AuditReport(BaseModel):
    version: str
    laws: list[dict]
    top_cited: list[dict]
    empty_results_by_criterion: list[dict]
    stale_verification_chunks: list[dict]
    chunks_with_empty_tags: list[dict]


class RagQueryLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | None = None
    analysis_id: UUID | None = None
    criterion_id: str | None = None
    query_text_hash: str
    corpus_version: str
    top_k: int
    threshold: float
    filter_tags: list[str] | None = None
    filter_law_ids: list[str] | None = None
    results_count_total: int
    results_count_above_threshold: int
    top_score: float | None = None
    queried_at: datetime
    expires_at: datetime
```

## Enumerations

```python
# corpus/domain/enums.py
from django.db import models

class LegalDocumentStatus(models.TextChoices):
    IN_FORCE = "in_force"
    REPEALED = "repealed"
    IN_FORCE_WITH_AMENDMENTS = "in_force_with_amendments"

class RelevanceLevel(models.TextChoices):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SeverityHint(models.TextChoices):
    OVERRIDE_CRITICAL = "override_critical"
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
```

## Protocol

```python
# corpus/domain/protocols.py
from typing import Protocol

class EmbeddingModel(Protocol):
    dim: int

    def encode(self, text: str) -> list[float]: ...

    def encode_batch(self, texts: list[str]) -> list[list[float]]: ...
```

## Commands and Queries

```python
# corpus/application/commands.py
from pathlib import Path
from pydantic import BaseModel
from corpus.domain.entities import CorpusVersion, LegalDocument, LegalChunk, RagQueryLog


class IngestCorpusVersion(BaseModel):
    version: str
    path: Path
    force: bool = False


class ActivateCorpusVersion(BaseModel):
    version: str


class CreateCorpusVersion(BaseModel):
    version: CorpusVersion


class CreateLegalDocument(BaseModel):
    document: LegalDocument


class CreateLegalChunk(BaseModel):
    chunk: LegalChunk


class LogRagQuery(BaseModel):
    entry: RagQueryLog
```

```python
# corpus/application/queries.py
from uuid import UUID
from shared.domain.entities.cqrs import BaseGetAttributes, BaseFilterAttributes, Query


class GetActiveCorpusVersion(BaseGetAttributes, Query):
    pass


class GetChunkByAnchor(BaseGetAttributes, Query):
    law_id: str
    anchor: str
    corpus_version: str


class SearchChunks(BaseFilterAttributes, Query):
    corpus_version: str
    embedding: list[float]
    top_k: int = 5
    threshold: float = 0.65
    filter_tags: list[str] | None = None
    filter_law_ids: list[str] | None = None
    prefer_anchors: list[str] | None = None
```

## New Dependencies

| Package | Version | Reason |
|---|---|---|
| `sentence-transformers` | ≥ 2.5 | Embedding model |
| `torch` | ≥ 2.1 | Model backend (CPU OK) |
| `pgvector` | ≥ 0.3 | `pgvector.django.VectorField` + cosine operators |
| `pyyaml` | ≥ 6.0 | Frontmatter parsing |
| `markdown-it-py` | ≥ 3.0 | Markdown body parsing |
| `unidecode` | ≥ 1.3 | Tag normalization |

OS deps: nothing new beyond standard Python build tools.

---

## Story: US-01 — Ingest a corpus version

Reference code, full happy path, error scenarios are covered in `COMPLETE_FLOWS.md` Flow 1. Implementation maps 1:1.

### Files to Create

- `corpus/application/services/corpus_ingestion_service.py`
- `corpus/infrastructure/parsing/markdown_parser.py`
- `corpus/infrastructure/parsing/frontmatter_validator.py`
- `corpus/infrastructure/django/management/commands/corpus_ingest.py`
- `corpus/infrastructure/django/migrations/0001_initial.py` (if F8 doesn't already declare the four tables)

Note on the migration: `_shared/GLOBAL_ASSUMPTIONS.md` §11 says `platform` owns all persistent tables. The corpus tables can either: (a) stay declared in `platform` (with the F8 plan owning the migration), or (b) move to `corpus` (with F3 owning the migration). **Decision**: option (b) — the `corpus_version`, `legal_document`, `legal_chunk`, `rag_query_log` tables are owned by the `corpus` app. F8 still declares the FK from `contract_analysis.corpus_version` (forward reference; Django allows string-app reference `"corpus.CorpusVersionModel"`).

### Test Cases

- [ ] Valid markdown set → IngestionReport with expected counts
- [ ] `--force` re-ingests after deleting prior rows
- [ ] Duplicate anchor → IntegrityError + rollback
- [ ] Missing frontmatter field → ParseError + rollback
- [ ] Embedding model unavailable → fail clean
- [ ] One file with 20 articles → batched embedding of all 20
- [ ] Manifest in CorpusVersion matches per-law counts

---

## Story: US-02 — Build and store embeddings

### Files to Create

`corpus/infrastructure/embeddings/sentence_transformer_adapter.py`:

```python
import os
import threading
import numpy as np
from sentence_transformers import SentenceTransformer
from corpus.domain.protocols import EmbeddingModel

_model: SentenceTransformer | None = None
_lock = threading.Lock()


def get_model() -> SentenceTransformer:
    global _model
    with _lock:
        if _model is None:
            name = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            cache_folder = os.getenv("EMBEDDING_MODEL_CACHE_DIR", "/var/cache/casa-segura/models")
            _model = SentenceTransformer(name, cache_folder=cache_folder, device=os.getenv("EMBEDDING_DEVICE", "cpu"))
    return _model


def warm_up_embedding_model() -> None:
    """Call once at process startup to amortize the first-load cost."""
    m = get_model()
    _ = m.encode("Casa Segura warm-up.")


class SentenceTransformerEmbedding(EmbeddingModel):
    dim = 384

    def encode(self, text: str) -> list[float]:
        m = get_model()
        v = m.encode(text, normalize_embeddings=True)
        return v.tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        m = get_model()
        batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
        v = m.encode(texts, batch_size=batch_size, normalize_embeddings=True)
        return v.tolist()
```

### Test Cases

- [ ] `encode("hola mundo")` returns length-384 vector
- [ ] L2 norm of the returned vector ≈ 1.0
- [ ] Same text → same vector (deterministic)
- [ ] Batch encode preserves order
- [ ] Warm-up succeeds even when DB unavailable (model has no DB dependency)

---

## Story: US-03 — F4 queries relevant articles

### Files to Create

- `corpus/application/services/legal_citation_service.py`
- `corpus/application/services/hybrid_matcher.py`
- `corpus/infrastructure/parsing/article_regex.py` (regexes from PRD §6.2)

### Test Cases

- [ ] Pure semantic query returns sorted list above threshold
- [ ] `prefer_anchors=["art-12"]` prioritizes the explicit anchor
- [ ] Empty result when top score < threshold
- [ ] Hybrid match on "Art. 1605 CC" returns the exact chunk with score 1.0
- [ ] Filter tags match → restricted result set
- [ ] Filter law_ids match → restricted result set
- [ ] Race between query and corpus reload safely sees a single version

---

## Story: US-04 — Cite-or-stay-silent discipline

Enforced inside `LegalCitationService.retrieve_legal_basis` filter step. Returns `[]` when no result above threshold. Logs `top_score`.

### Test Cases

- [ ] Threshold 0.65, best 0.55 → []
- [ ] Threshold 0.50, best 0.55 → [LegalReference]
- [ ] Per-call threshold override works

---

## Story: US-05 — Versioning

`LegalCitationService` always receives `corpus_version` explicitly. There is no implicit "latest" lookup in retrieval. The "latest" pointer is only used at analysis-creation time by F2/F4 when reading the active rubric+corpus pair.

### Test Cases

- [ ] Activate v2 while a job is still running with v1 → job's results pinned to v1
- [ ] Deactivated version still queryable by its name
- [ ] Active partial-unique index prevents two `is_active=true` rows

---

## Story: US-06 — Operator audits corpus coverage

### Files to Create

`corpus/infrastructure/django/management/commands/corpus_audit.py`

### Test Cases

- [ ] Audit lists each law with counts
- [ ] `--export report.csv` writes CSV
- [ ] Top-cited query aggregates `rag_query_log` correctly
- [ ] Stale-verification filter (`last_verified < NOW() - 6 months`) returns expected rows

---

## Part 2 — Staged Execution Plan

### Codebase Alignment Rules

- Standard from `_shared/GLOBAL_ASSUMPTIONS.md` plus:
- `corpus_version`, `legal_document`, `legal_chunk`, `rag_query_log` are owned by the `corpus` app (its migrations folder).
- `pgvector.django.VectorField(dimensions=384)` for the embedding column.
- HNSW index created via raw SQL in `RunSQL` migration op.
- Embedding model loaded once per process; thread-safe singleton.
- All retrievals must be filtered by `corpus_version`; never implicit "latest".

### Stage Overview

| # | Stage | Deliverable |
|---|---|---|
| 1 | Domain entities & enums & exceptions & EmbeddingModel Protocol | Pydantic + Protocol |
| 2 | Commands, queries | CQRS contracts |
| 3 | Handlers | Plain functions |
| 4 | Service classes | `CorpusIngestionService`, `LegalCitationService`, `HybridMatcher` |
| 5 | Embedding adapter | `SentenceTransformerEmbedding` |
| 6 | Markdown parser | `MarkdownCorpusParser` + `FrontmatterValidator` + article regex |
| 7 | Django models + migration | `CorpusVersionModel`, `LegalDocumentModel`, `LegalChunkModel`, `RagQueryLogModel`, HNSW index via RunSQL |
| 8 | Repositories | Four repositories, including `cosine_search` |
| 9 | Management commands | `corpus_ingest`, `corpus_activate`, `corpus_list`, `corpus_query`, `corpus_audit` |
| 10 | Internal endpoint | `InternalRagQueryView` + serializers + URL |
| 11 | Tests | Unit + integration with `respx` (none here — no HTTP outbound), real Postgres test DB with pgvector |
| 12 | Observability | Prometheus metrics for retrieval latency, score distribution, empty rate |
| 13 | Documentation | `corpus/README.md` + corpus authoring guide |

### Stage 7 detail — Migration with HNSW

```python
# corpus/infrastructure/django/migrations/0001_initial.py
from django.db import migrations, models
from pgvector.django import VectorField


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;", reverse_sql=migrations.RunSQL.noop),
        migrations.CreateModel(
            name="CorpusVersionModel",
            fields=[
                ("version", models.TextField(primary_key=True, serialize=False, help_text="Corpus version tag, e.g. 2026-05-10.")),
                ("released_at", models.DateTimeField(auto_now_add=True, help_text="Publication time.")),
                ("laws_count", models.IntegerField(help_text="Number of laws.")),
                ("articles_count", models.IntegerField(help_text="Total articles.")),
                ("chunks_count", models.IntegerField(help_text="Total chunks.")),
                ("manifest", models.JSONField(help_text="Per-law summary.")),
                ("changelog", models.TextField(null=True, blank=True, help_text="Notes vs. prior version.")),
                ("is_active", models.BooleanField(default=False, help_text="Whether this is the version new analyses use.")),
                ("created_by", models.TextField(null=True, blank=True, help_text="Operator who ran ingestion.")),
                ("created_at", models.DateTimeField(auto_now_add=True, help_text="Created timestamp.")),
            ],
            options={"db_table": "corpus_version"},
        ),
        # ... LegalDocumentModel, LegalChunkModel (with VectorField), RagQueryLogModel ...
        migrations.RunSQL(
            "CREATE UNIQUE INDEX idx_corpus_version_active ON corpus_version (is_active) WHERE is_active = TRUE;",
            reverse_sql="DROP INDEX IF EXISTS idx_corpus_version_active;",
        ),
        migrations.RunSQL(
            "CREATE INDEX idx_legal_chunk_embedding ON legal_chunk USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);",
            reverse_sql="DROP INDEX IF EXISTS idx_legal_chunk_embedding;",
        ),
        migrations.RunSQL(
            "CREATE INDEX idx_legal_chunk_tags ON legal_chunk USING GIN(tags);",
            reverse_sql="DROP INDEX IF EXISTS idx_legal_chunk_tags;",
        ),
        migrations.RunSQL(
            "CREATE INDEX idx_legal_chunk_relevance ON legal_chunk USING GIN(relevance_for_findings);",
            reverse_sql="DROP INDEX IF EXISTS idx_legal_chunk_relevance;",
        ),
    ]
```

### Stage 12 — Metrics

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `f3_retrieve_latency_seconds` | Histogram | `path` (hybrid/semantic) | Latency budget |
| `f3_retrieve_results_total` | Counter | `outcome` (`hit`/`empty`) | Empty rate |
| `f3_retrieve_score_top` | Histogram | — | Score distribution |
| `f3_ingest_chunks_total` | Counter | `version` | Chunks created |
| `f3_active_corpus_version` | Gauge | `version` | Visibility |
| `f3_embedding_model_load_seconds` | Gauge | — | Startup time |

---

## Error Codes (canonical list owned by F3)

| Code | Description |
|---|---|
| `CORPUS_VERSION_NOT_FOUND` | Requested version does not exist |
| `CORPUS_VERSION_EXISTS` | Cannot re-ingest without `--force` |
| `CORPUS_PARSE_ERROR` | Markdown frontmatter or body malformed |
| `CORPUS_DUPLICATE_ANCHOR` | Same anchor twice in one law in one version |
| `EMBEDDING_MODEL_UNAVAILABLE` | Cannot load sentence-transformers model |
| `EMBEDDING_DIM_MISMATCH` | Computed vector dim differs from configured |
| `CORPUS_INVALID_FRONTMATTER` | Frontmatter validation failed (missing required field) |

---

## Configuration matrix (F3 env vars)

| Variable | Default | Purpose |
|---|---|---|
| `EMBEDDING_MODEL_NAME` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Model id |
| `EMBEDDING_DIMENSIONS` | 384 | Sanity check |
| `EMBEDDING_MODEL_CACHE_DIR` | `/var/cache/casa-segura/models` | Local cache |
| `EMBEDDING_DEVICE` | `cpu` | `cuda` if GPU |
| `EMBEDDING_BATCH_SIZE` | 32 | Batch size for `encode_batch` |
| `RAG_DEFAULT_THRESHOLD` | 0.65 | Cite-or-stay-silent threshold |
| `RAG_DEFAULT_TOP_K` | 3 | Default top_k |
| `RAG_QUERY_LOG_SALT` | (random) | Salt for hashing finding text in logs |
| `RAG_QUERY_LOG_TTL_DAYS` | 90 | F8 cleanup |
| `CORPUS_WARMUP_ON_READY` | `false` (set `true` in worker) | Warm model at AppConfig.ready() |

---

**End of document.**
