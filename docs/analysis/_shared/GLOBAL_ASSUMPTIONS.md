# Global Assumptions & Cross-PRD Decisions — Casa Segura

> **Generated:** 2026-05-15
> **Last realignment:** 2026-05-15 (stack flipped to **Django 5.2 LTS**)
> **Owner of this file:** `backend-requirements-analyst`
> **Purpose:** Cross-cutting decisions, contradictions, and assumed defaults that apply to **every** per-feature implementation plan (F1–F8). Every per-feature `EVALUATION_COVERAGE.md` references this file for items that are not feature-local.

---

## 1. Architecture stack — RESOLVED (Django 5.2 LTS)

The backend stack for Casa Segura is **Django 5.2 LTS + Django REST Framework + DDD/Clean Architecture + CQRS**, aligned with the skill's `architecture-conventions.md`. Django 5.2 was released April 2025 and is the active LTS through April 2028, so it is the right anchor for a multi-year product. Async views are first-class in Django 5; DRF is used for the public/internal REST surface; Celery (Redis broker) is the async-task runtime mandated by the conventions.

### Why this stack

| Concern | Choice | Why |
|---|---|---|
| HTTP framework | Django 5.2 LTS + DRF 3.15+ | Mandated by user decision; long support; battle-tested ORM, admin, migrations, signals; aligned with the skill conventions |
| Domain layer | Pydantic v2 BaseModel | Framework-free, mandated by skill conventions |
| Persistence | Django ORM on Postgres 15+ | Native to Django; supports JSONB and ArrayField via `django.contrib.postgres`; works with `pgvector` via `pgvector-python` + `pgvector.django` |
| Vector search | `pgvector` extension + `pgvector.django.VectorField` | Required by F3; mature integration |
| Async tasks | Celery 5.4+ (Redis broker) + `django-celery-beat` for scheduled tasks | Mandated by skill `@shared_task` pattern |
| Sessions / queues | Redis 7+ | Streams for F1→F2→F4 pipeline; key-expiry notifications for WhatsApp sessions; rate limiting |
| Migrations | Django migrations (no Alembic) | Native; per-module `migrations/` directories |
| Test framework | `pytest-django` + `pytest-asyncio` | DB savepoint fixtures, factory-boy |
| HTTP client (outgoing) | `httpx` (sync + async) | OpenRouter, Zavu, SMTP-providers via HTTP transactional APIs |
| LLM | OpenRouter (HTTP); abstracted in adapters | Idempotency keys per call |
| OCR | `pypdf`, `pdf2image`+`poppler-utils`, `pytesseract`+`tesseract-ocr-spa`, `pillow-heif`+`libheif` | Per F1 PRD |
| Reporting | `Jinja2`+`WeasyPrint` | Per F6 PRD (DRF templating is not the right tool for PDF; we keep DRF for JSON only) |
| KMS | AWS KMS / GCP KMS / `libsodium` (local) | Per F7 §6.4 |
| Settings | Django settings (`config/settings/{base,dev,prod}.py`), env via `django-environ` or `pydantic-settings` | Django-native |
| Containers | One image `casa-segura-django` (multi-target build for `web`, `worker`, `beat`); OCR OS deps only in worker image | — |
| CI | Black (line 119), isort (Django profile), mypy, `pytest-django`, `django-check`, `makemigrations --check` | — |

### Adopted module layout (used by every feature plan)

Per the skill's `architecture-conventions.md` exactly:

```
{module_name}/                              # at project root, no apps/ prefix
├── domain/
│   ├── __init__.py
│   ├── entities.py          # Pydantic v2 BaseModel domain models — no ORM
│   ├── enums.py             # StrEnum / IntEnum / Django TextChoices business enumerations
│   └── exceptions.py        # Module-specific DomainException subclasses (only when needed)
│
├── application/
│   ├── __init__.py
│   ├── commands.py           # CQRS command definitions (Pydantic BaseModel wrapping entities)
│   ├── queries.py            # CQRS query definitions (BaseFilterAttributes / BaseGetAttributes + Query)
│   ├── contracts/
│   │   └── messages.py       # Queue envelopes (Pydantic) for cross-feature stream messages
│   ├── handlers/
│   │   └── {entity}_handlers.py    # Plain functions (command/query, repository) -> result
│   └── services/
│       └── {entity}_service.py     # Plain classes orchestrating handlers
│
└── infrastructure/
    ├── __init__.py
    ├── django/                  # Django/DRF adapter
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py              # AppConfig with name="{module}.infrastructure.django", label="{module}"
    │   ├── models.py            # Django ORM models (data shape only, no logic)
    │   ├── repositories.py      # DjangoFullRepository[T, K] subclasses
    │   ├── serializers.py       # DRF serializers
    │   ├── views.py             # DRF ViewSets / APIViews
    │   ├── urls.py              # URL patterns
    │   ├── permissions.py       # Per-module DRF permission classes (only when needed)
    │   ├── signals.py           # Django signals (only if required)
    │   └── migrations/
    │       └── __init__.py
    ├── celery/                  # Async tasks
    │   └── {module}_tasks.py    # @shared_task functions
    ├── llm/                     # OpenRouter clients (when needed)
    │   └── openrouter_client.py
    ├── external/                # External adapters: Zavu, SMTP, KMS
    │   └── ...
    ├── redis/                   # Redis Streams publishers/consumers, session stores
    │   └── ...
    └── mongo/                   # Only if module reads MongoDB (not used by Casa Segura today)
```

### Casa Segura modules and ownership

```
casa_segura/                # repository root (Django project)
├── manage.py
├── config/
│   ├── settings/{base,dev,prod}.py
│   ├── urls.py
│   ├── asgi.py
│   ├── wsgi.py
│   └── celery.py            # Celery app, autodiscover tasks
├── platform/                 # F8: shared schema, retention, audit, scheduler
├── ingestion/                # F1: uploads, OCR, language detection
├── classification/           # F2: contract type, project name, economic raw extraction
├── corpus/                   # F3: RAG, legal corpus
├── rubric/                   # F4: criteria evaluation, scoring
├── economics/                # F5: derivations, benchmarks
├── reports/                  # F6: HTML+PDF generation
├── delivery/                 # F7: email, WhatsApp, web link
└── shared/                   # Common: repositories ABC, exceptions, pagination, settings, KMS, circuit breaker
```

`INSTALLED_APPS` lists every module's `infrastructure.django` AppConfig, e.g. `"ingestion.infrastructure.django"`. `MIGRATION_MODULES` maps the short label to its per-module migrations directory, e.g. `{"ingestion": "ingestion.infrastructure.django.migrations"}`. Module URL files are mounted in `config/urls.py` under the `/v1/` prefix.

### Conventions adopted verbatim from the skill

- **Domain layer** = Pydantic v2 models only; no Django imports
- **Application layer** = depends only on Domain; no ORM, no HTTP, no Django
- **Infrastructure layer** = adapts Django/DRF/Celery/Redis to contracts defined in Domain+Application
- **Commands**: Pydantic BaseModel wrapping a domain entity (e.g. `CreateAccount(BaseModel)` with field `account: Account`)
- **Queries**: inherit `BaseFilterAttributes` / `BaseGetAttributes` from `shared.domain.entities.cqrs` plus the `Query` ABC
- **Handlers**: plain functions accepting `(command|query, repository)` returning the result; one file per domain concept under `application/handlers/`
- **Services**: plain classes with repositories injected via `__init__(*, ..._repository=...)`; call handlers; do orchestration
- **Models**: inherit `SoftDeleteObject, ModelWithTimeStamps`; every FK has explicit `related_name`; every model has `__str__`; **every field has `help_text`** (mandatory for Swagger, AI analysis)
- **Repositories**: subclass `DjangoFullRepository[T, K]` from `shared.infrastructure.django.repositories`; implement `to_entity()` and `to_orm_model()`; override `_optimize_queryset()` for `select_related` / `prefetch_related`
- **Serializers**: never `fields = '__all__'`; separate `{Model}Serializer` (read) and `{Model}WriteSerializer` (write) when shapes differ
- **Views**: services and repositories as **class-level attributes**, NOT in `__init__`; `permission_classes` explicit; `@extend_schema` from `drf-spectacular` for OpenAPI
- **URLs**: `SimpleRouter` for ViewSets; `urlpatterns = router.urls` at the bottom
- **Celery tasks**: `@shared_task(name="{module}.task_name")`; accept IDs only, never model instances; instantiate services/repositories inside the task
- **Exceptions**: `DomainException(message, code, status, *, extra=None)` base from `common.domain.exceptions.core`

### Permission system — adapted for Casa Segura

Casa Segura **has no user accounts** (`PRD_GENERAL` §2 lists this out of scope). The skill's `IsExpertelStaff | IsClientAdministrator | IsViewer` permissions do **not** apply. Instead, we define a small per-project permission set in `shared/infrastructure/django/permissions.py`:

| Class | Behavior |
|---|---|
| `AllowAny` | Reuse DRF's built-in for public endpoints (`/v1/contracts/submit`, `/r/{short_id}`, status polling) |
| `HasInternalAuthHeader` | Requires header `X-Internal-Auth` matching the env-configured shared secret; used for `/v1/internal/...` debug endpoints |
| `ValidatesZavuSignature` | Custom permission that verifies the `X-Zavu-Signature` HMAC before the view body runs; used on the webhook |
| `IsCapabilityHolder` | Used on resend endpoints: receives the `public_short_id` from the URL and the destination from the body; validates `salt+sha256(destination) == delivery_target_hash` |

`combine_with_|` is not used because there is no role overlap to compose. Every endpoint explicitly states its single permission class.

### Pagination, filters, annotations, repository base classes

We reuse the skill's `shared/domain/entities/{cqrs,repositories,specifications,annotations,pagination}.py` verbatim:

- `Command`, `Query`, `BaseFilterAttributes`, `BaseGetAttributes`
- `ReadOnlyRepository[T]`, `WriteOnlyRepository[T]`, `BaseRepository[T]` (abstract)
- `DjangoReadRepository[T, K]`, `DjangoWriteRepository[T, K]`, `DjangoFullRepository[T, K]`
- `Specification`, `FieldSpec`, `CompositeSpec`
- `Annotation` classes
- `QuerySet[T]`, `QuerySetPagination`, `PaginatedQuerySet`

These ship in the `shared/` module; every feature module imports from them and does **not** redeclare them.

### Naming-convention mapping (Casa Segura specifics on top of the skill)

| Skill default | Casa Segura |
|---|---|
| `infrastructure/django/models.py` | unchanged |
| `infrastructure/django/repositories.py` | unchanged |
| `infrastructure/django/views.py` | unchanged |
| `infrastructure/django/serializers.py` | unchanged |
| `infrastructure/django/urls.py` | unchanged |
| `infrastructure/celery/{module}_tasks.py` | unchanged |
| `IsExpertelStaff | IsClientAdministrator | IsViewer` | Replaced by `AllowAny`, `HasInternalAuthHeader`, `ValidatesZavuSignature`, `IsCapabilityHolder` (above) |
| `drf-spectacular @extend_schema` | unchanged |
| Existing Casa Segura model base classes | New `shared/infrastructure/django/mixins.py` adds `SoftDeleteObject` (re-export from `softdelete`) and `ModelWithTimeStamps` (provides `created_at` auto_now_add, `updated_at` auto_now) — matching the skill's expected base |

### Action required from the user

> No remaining stack ambiguity. The user has confirmed Django 5.2 LTS as the canonical backend on 2026-05-15.

---

## 2. CRITICAL scope note — ARCHITECTURE.md vs. PRDs

`docs/ARCHITECTURE.md` centers on the **original two-flow MVP** narrative (billboard photo + contract PDF, blacklist- and reputation-first). `PRD_GENERAL.md` §2 and per-feature PRDs F1–F8 describe the **full product** (ingestion pipeline, rubric, RAG corpus, retention, `Project`, etc.).

**Stack resolution (implementation):** `ARCHITECTURE.md`, `BE-SERVICES.md`, and the legal-layer architecture doc are aligned on **Django 5.2 LTS + DRF**, **Django ORM + Django migrations**, **Celery + Redis**, **PostgreSQL 15 + pgvector**, and **Pydantic v2** domain DTOs / queue payloads ([ADR-0001](../../adr/ADR-0001-django-backend-stack.md)).

**Product resolution:** **Canonical behavior, schema, and business rules** remain `PRD_GENERAL.md` + F1–F8 + `DOMAIN_MODEL.md` + `FEATURES_MAP.md`. REST paths in PRDs (for example `POST /v1/contracts/submit`) are **URL contracts** implemented with **Django/DRF**, not FastAPI.

---

## 3. CRITICAL contradiction — `delivery_status` value sets

Two PRDs publish overlapping but **incompatible** enumerations for `contract_analysis.delivery_status`:

- **PRD_F8 §5.1** (canonical): `'pending', 'queued', 'sent_email', 'sent_whatsapp', 'available_link', 'expired', 'failed'`
- **`RUBRICA_CONTRATO.md` §12.2**: `'pending', 'sent_email', 'sent_whatsapp', 'available_link', 'expired'` (missing `queued`, `failed`)
- **PRD_F1 §5.1** (`contract_submission.processing_status`, distinct column with overlap): `'received', 'extracting', 'extracted', 'classifying', 'analyzing', 'completed', 'failed_extraction', 'failed_classification', 'failed_analysis', 'rejected_language', 'rejected_type', 'rejected_size', 'expired'`
- **PRD_F7 §3 US-01** narrative: the system creates a `DeliveryRequest` with `status='queued'`, then `sending`, `delivered`, `failed`, `expired` (for the **delivery_request** table, not `contract_analysis`).

**Severity:** MODERATE. The `RUBRICA` enum is older and `PRD_F8` supersedes it. The `delivery_request.status` (`queued/sending/delivered/failed/expired`) is a separate column from `contract_analysis.delivery_status` and the two intentionally use overlapping vocabulary.

**Resolution applied:** PRD_F8 §5.1 is canonical. `RUBRICA_CONTRATO.md` will need an editorial alignment but does not change implementation. Each per-feature plan uses the F8 values verbatim. Encoded as Django `TextChoices` in `platform/domain/enums.py`.

---

## 4. CRITICAL contradiction — Project name normalization rules

`PRD_F2 US-02` defines normalization rules (lowercase, remove accents, drop generic words `proyecto`, `residencial`, `condominio`, `urbanización`, `lotificación`, `complejo`, `parque`). `DOMAIN_MODEL.md` §3.1 only says "lowercase, no accents, no special characters, no redundant spaces" — it does **not** mention dropping generic words.

**Severity:** MODERATE. The F2 rule is more aggressive and risks collapsing distinct projects (e.g., "Residencial El Roble" vs. "El Roble" both → `el roble`). The DOMAIN_MODEL rule is more conservative.

**Resolution applied:** Use the **F2 rule** (more specific), accept the risk of collapsing legitimately distinct projects, and document it in F2's evaluation coverage as `OQ-N2`. The PRD already declares the system does **not** verify project names externally.

---

## 5. MODERATE contradiction — Disclaimer code consistency

`PRD_F1 US-01` defines `DISCLAIMER_REQUIRED` (HTTP 400) when the disclaimer is not accepted. `PRD_GENERAL.md` US-01 states "Before processing, the system shows the user the disclaimer" — implies the disclaimer is enforced **after** the upload page, not at the API level. The F1 implementation moves it to the API contract, which is acceptable but the frontend must echo it. No code conflict; documented for transparency.

---

## 6. MODERATE contradiction — Idempotency vs. rubric version

`PRD_F1 BR-03` says: deduplication by `submission_hash` returns the prior `analysis_id` **unless the current rubric version differs**, in which case it re-processes. `PRD_F4 BR-10` says: re-evaluating with a new rubric version creates a **new analysis**, not an update. These are consistent only if F1 creates a new `contract_analysis` row pointing to the same `submission_hash` and the response is treated as "new analysis with this content". `PRD_F2 BR-11` calls this "Idempotency: the same analysis_id with the same rubric_version is not reclassified", which is the consistent interpretation.

**Resolution applied:** A new rubric version triggers a new `contract_analysis` row, sharing `submission_hash` and `project_id` with the prior one. The HTTP response uses `409 Conflict` only when an analysis with `(submission_hash, rubric_version)` already exists.

---

## 7. Open question (cross-cutting, not blocking) — Reclassification threshold

`PRD_F2 US-03` sets the leasing-reclassification threshold at "≥ 4 of 6 indicators". `PRD_F2 §10 Open Question 1` lists this as an open decision. The rubric §3 says: "if the document is presented as 'compraventa' but contains the six leasing indicators". The strict reading of the rubric implies all six; the F2 reading is the relaxed 4-of-6.

**Resolution applied:** Use the **F2 ≥4 of 6** threshold (the PRD that defines the engine), and flag in F2's `EVALUATION_COVERAGE.md` as a configurable parameter (`LEASING_RECLASSIFICATION_THRESHOLD`, default 4).

---

## 8. Open question (cross-cutting) — `evidence_clause_snippet` survival

`PRD_F4 BR-16` states `evidence_clause_snippet` (up to 500 chars) IS persisted inside `contract_analysis.findings`, anonymized after 90 days. `PRD_F8 BR-00` confirms this is the **only** allowed channel for contract text persistence. `RUBRICA_CONTRATO.md` §12.4 states no clauses are persisted. Internally consistent once the canonical reading is adopted: F4/F8 (newer) supersede the rubric note. Snippets are bounded (500 chars), discarded at 90 days, never exposed in logs, never exposed to other users (only the report owner accessing their link).

**Resolution applied:** `evidence_clause_snippet` is persisted within `findings` JSONB, subject to anonymization. Treated identically across all feature plans.

---

## 9. Open question — `submission_hash` survival after anonymization

`PRD_F8 §10 Open Question 6` proposes preserving `submission_hash` after anonymization for future deduplication. `DOMAIN_MODEL.md` §3.2 says "submission_hash is preserved after anonymization for future deduplication". `PRD_F1 BR-03` relies on this for idempotency.

**Resolution applied:** **YES**, `submission_hash` survives anonymization. Documented in F8's `EVALUATION_COVERAGE.md`.

---

## 10. Decided cross-cutting defaults

| Parameter | Default | Source |
|---|---|---|
| Public link TTL (`LINK_TTL_DAYS`) | 30 | F7 BR-06, RUBRICA §13.3 |
| Anonymization deadline (`ANONYMIZATION_AFTER_DAYS`) | 90 | F8 BR-03 |
| Transient cleanup interval | 15 minutes | F8 §6.2 |
| Public short id format | `CS-{YYYY}-{6 base32 chars}` | DOMAIN §3.2 |
| Embedding model | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dim) | F3 §3 US-02 |
| RAG similarity threshold (default) | 0.65 (cosine) | F3 BR-06 |
| Vision LLM (default) | `anthropic/claude-sonnet-4` via OpenRouter | F1 US-06, F2 §6.3 |
| F4 rubric LLM temperature | 0.1 | F4 BR-07 |
| F4 concurrency | 8 | F4 BR-08 |
| Disclaimer copy | "Esto no es asesoría legal" (Spanish, "tú") | PRD_GENERAL BR-07 |
| Project metadata flag for placeholders | `metadata.placeholder = true` | F2 US-02, F8 BR-07 |
| KMS provider (default) | `aws` (allow `gcp`, `local`) | F7 §6.4 |
| Database | Postgres 15+ with pgvector | F8 BR-10 |
| Migration tool | Django migrations | (Casa Segura decision) |
| Currency conversion (SVC→USD) | Fixed parity 8.75 SVC/USD | F5 BR-04 |
| Art. 1686 CC warning policy | `always` | F6 BR-08 |
| Background task framework | Celery 5.4+ on Redis broker | (Casa Segura decision) |
| Periodic task framework | `django-celery-beat` | (Casa Segura decision) |

---

## 11. Cross-cutting domain entities (shared across modules)

Per `DOMAIN_MODEL.md`, all features share the same entity vocabulary. Entities are partitioned into the modules below; **every** entity has exactly one owning module that holds its `domain/entities.py` Pydantic class and its `infrastructure/django/models.py` Django ORM class. Other modules import from there.

| Entity | Owner module | Notes |
|---|---|---|
| `Project` | `platform` (F8 defines schema and the matching logic) | Read by F2, F6 |
| `ContractAnalysis` | `platform` (F8 defines schema; F2/F4/F5/F6/F7 write per-column) | Central entity |
| `ContractSubmission` | `ingestion` (F1) | Transient |
| `OcrJob` | `ingestion` (F1) | Transient |
| `DeliveryRequest` | `delivery` (F7) | Transient |
| `LegalDocument`, `LegalChunk`, `CorpusVersion` | `corpus` (F3) | Catalog |
| `Criterion`, `RubricVersion` | `rubric` (F4 functional; F8 declares schema) | Catalog |
| `EconomicBenchmark`, `BenchmarkVersion` | `economics` (F5 functional; F8 declares schema) | Catalog |
| `RagQueryLog` | `corpus` (F3) | Observability |
| `JobExecutionLog`, `PrivacyAuditLog` | `platform` (F8) | Cross-cutting |
| `ReportGenerationLog` | `reports` (F6) | Optional |
| `ClassificationJob` | `classification` (F2) | Optional |

Entities owned by `platform` (Project, ContractAnalysis) have their Django models registered under the `platform.infrastructure.django` AppConfig with label `platform`. Other features import the Pydantic entity from `platform.domain.entities` and read/write through `platform`-provided repositories or through their own repositories that point to the same models with explicit `app_label='platform'`. The latter is preferred: each feature owns a thin `repositories.py` exposing exactly the queries it needs over the shared models.

---

## 12. Cross-cutting design patterns (applied everywhere)

| Pattern | Where it appears | Why |
|---|---|---|
| **Repository (DjangoFullRepository)** | Every module's `infrastructure/django/repositories.py` | Isolates Django ORM from application/domain |
| **CQRS** | Every module's `application/commands.py` + `queries.py` + `handlers/` | Separates write intent from read intent |
| **Pipes & Filters** | F1→F2→F4/F5→F6→F7 pipeline | Each feature is a stage; Redis Streams or Celery chord links them |
| **Strategy** | F1 OCR routing (`pypdf` / `vision_llm` / `tesseract`) | Pluggable extraction strategies |
| **Circuit breaker** | F1 OpenRouter calls, F7 SMTP/Zavu calls | Resilience against external provider failures |
| **Idempotency key** | F1 LLM calls, F7 deliveries | Avoid duplicate cost/messages on retry |
| **Periodic task (Celery Beat)** | F8 retention jobs | Time-driven cleanup |
| **Anti-corruption layer** | `infrastructure/external/*` and `infrastructure/llm/*` | Translates external models to domain entities |
| **Versioned catalog** | RubricVersion, CorpusVersion, BenchmarkVersion | Reproducibility of past analyses |
| **Versioned + immutable** | Same as above + `is_active` flag with partial unique index | Only one version is "current"; old versions are accessible |
| **Capability token** | `public_short_id` for `/r/{id}` endpoint | No auth; entropy substitutes authentication |
| **Anonymization (bucket)** | F8 `anonymize_economic_summary` | Statistical preservation without re-identification |

---

## 13. Contracts between features (canonical message shapes)

These envelopes pass between features through Celery tasks (preferred for typed retries with backoff) and/or Redis Streams (for the high-throughput ingestion stage). They are **not** persisted in the database; they only exist in flight. Each feature's `IMPLEMENTATION_PLAN.md` references these shapes verbatim.

### Strategy

Two options coexist:
- **Celery task chain**: `F1 → F2 → F4+F5 (chord) → F6 → F7` via `chain()` and `chord()`. Each task takes IDs as inputs and re-loads state from the DB. Best when state is fully persisted between stages.
- **Redis Streams envelope**: Used when the in-memory `extracted_text` must travel between stages without persistence. Specifically, F1→F2 carries the extracted text in memory via a Redis Streams message with a short-TTL payload (≤ 300 s), then F2 acks and the payload is gone.

Casa Segura adopts a **hybrid**: the F1→F2 link uses Redis Streams (extracted text must not be persisted); every other link uses Celery chains keyed on `analysis_id`.

### F1 → F2 envelope (`extraction_done` — Redis Streams)

```python
class ExtractionDone(BaseModel):
    submission_id: UUID
    analysis_id: UUID  # F1 creates the contract_analysis stub with public_short_id
    extracted_text: str  # in-memory only; never persisted to Postgres
    extraction_metadata: ExtractionMetadata

class ExtractionMetadata(BaseModel):
    strategy_used: ExtractionStrategy
    pages_processed: int
    pages_failed: int
    tokens_consumed: int
    language_detected: str
    language_confidence: float
```

Stream: `ingestion.to_classification`. Consumer group: `classification`. Message TTL via `XADD` with `MAXLEN ~ 10000`.

### F2 → F4 + F5 envelope (`classification_done` — Redis Streams)

```python
class ClassificationDone(BaseModel):
    submission_id: UUID
    analysis_id: UUID
    project_id: UUID
    extracted_text: str  # still in-memory
    classification: ClassificationResult
    economic_fields_raw: EconomicFieldsRaw
    elements_detected: ElementsDetected
```

Stream: `classification.to_rubric_and_economics`. Two consumer groups: `rubric` and `economics`.

### F5 → F4 envelope (`economic_done` — Celery)

```python
@shared_task(name="rubric.absorb_economic_summary")
def absorb_economic_summary(analysis_id: str) -> None:
    ...
```

F5 writes `economic_summary` to `contract_analysis` and triggers the task. F4 reads from the DB.

### F4 → F6 → F7 (Celery chain)

```python
chain(
    rubric_tasks.finalize_analysis.s(analysis_id),
    reports_tasks.materialize_report.s(),
    delivery_tasks.deliver_to_user.s(),
).apply_async()
```

Each task reads its inputs from the DB by `analysis_id`. F6 does not persist; it computes HTML/PDF in-memory and hands the binary to F7.

---

## 14. Permission and authentication model

Casa Segura has **no user accounts** (PRD_GENERAL §2 "User accounts, login, or any persistent authentication" is out of scope). The endpoints fall into four categories, each implemented as a DRF permission class in `shared.infrastructure.django.permissions`:

| Category | DRF Permission | Used in |
|---|---|---|
| **Anonymous public** | `AllowAny` | `POST /v1/contracts/submit`, `GET /v1/contracts/{id}/status`, `GET /r/{short_id}` |
| **Capability-token** | `IsCapabilityHolder` (validates the destination hash against `delivery_target_hash`) | `POST /v1/contracts/{short_id}/resend`, `GET /v1/contracts/{short_id}/delivery-status` |
| **Internal ops** | `HasInternalAuthHeader` (header `X-Internal-Auth` matches shared secret) | `POST /v1/internal/...` debug endpoints, `POST /v1/internal/jobs/trigger/{name}` |
| **Webhook** | `ValidatesZavuSignature` (HMAC-SHA256 of body) | `POST /v1/zavu/webhook` |

`public_short_id` entropy is 30+ bits (`CS-{YYYY}-{6 chars base32}`). A rate-limiter (5 reqs/hour/IP) — implemented as a custom DRF throttle class `BurstSubmitThrottle` — is the principal abuse defense for `POST /v1/contracts/submit`.

---

## 15. Conventions reused across implementation plans

These items are short enough to fix once and reused across each plan instead of repeating the boilerplate.

- **Python target**: 3.11+
- **Django version**: 5.2 LTS
- **DRF version**: 3.15+
- **Style**: Black (line length 119), isort with Django profile + Black compatibility
- **Type hints**: PEP 604 union syntax (`X | None`, `list[str]`, `dict[str, int]`)
- **Settings management**: Django settings split into `config/settings/{base,dev,prod}.py`; env loading via `django-environ` (project-wide adopted)
- **Logging**: structured JSON via `structlog` integrated with Django logging; key conventions: `analysis_id`, `submission_id`, `feature`, `stage`, `cost_cents`, `tokens`, `elapsed_ms`
- **Metrics**: `django-prometheus` plus a side `prometheus_client` registry for Celery workers; exposed at `/metrics`
- **DB driver**: `psycopg[binary]` v3 (Django 5.2's preferred driver)
- **ORM**: Django ORM 5.2; `ArrayField`, `JSONField` from `django.contrib.postgres`; `VectorField` from `pgvector.django`
- **Migrations**: Django migrations per module under `{module}/infrastructure/django/migrations/`
- **Async tasks**: Celery 5.4+ with Redis broker; `@shared_task` only; tasks accept IDs not model instances; tasks instantiate services/repositories inside
- **Periodic tasks**: `django-celery-beat` with DatabaseScheduler; schedules declared in code at AppConfig.ready()
- **Containers**: One Dockerfile multi-target (`web`, `worker`, `beat`) sharing a base; OCR OS deps (`tesseract-ocr-spa`, `libheif`, `poppler-utils`) only in worker image
- **Testing**: `pytest-django` + `pytest-asyncio` + `pytest-cov` + `factory-boy`; fixtures isolate DB via savepoints; LLM and OpenRouter mocked at the HTTP transport level via `respx`
- **CI checks**: pre-commit (Black + isort + mypy strict), `pytest --cov`, `python manage.py makemigrations --check --dry-run`, `python manage.py check --deploy`
- **API docs**: `drf-spectacular` for OpenAPI; `@extend_schema` on every endpoint
- **HTTP client (outgoing)**: `httpx` (sync for Celery tasks, async for DRF views when needed)

---

## 16. Documents superseded or stale

| Document | Status | Action |
|---|---|---|
| `docs/ARCHITECTURE.md` | **Stack:** current (Django 5.2 LTS per ADR-0001). **Narrative:** simplified two-flow MVP; **canonical product scope** is PRDs + `DOMAIN_MODEL.md`. | Use for high-level diagrams; do not override F1–F8 behavior |
| `docs/STATUS.md` | Out of date; describes hour-marked hackathon plan | Ignore for the formal implementation plans |
| `.claude/skills/shared-references/architecture-conventions.md` | **Canonical for the layered DDD/CQRS structure**. Casa Segura adopts it directly with only the permission classes substituted (Section 1 above). | — |
| Per-feature PRDs F1–F8, `PRD_GENERAL.md`, `DOMAIN_MODEL.md`, `FEATURES_MAP.md`, `RUBRICA_CONTRATO.md` | **Canonical** for behavior, data, business rules. URL paths preserved verbatim. | All implementation plans align to these |

---

## 17. Items pending product confirmation

Items in this list block 100% PRD coverage. They are surfaced per-feature with the same codes and resolutions:

| ID | Question | Default applied | Required confirmation |
|---|---|---|---|
| `GQ-01` | LLM provider sustainability model | LLM cost capped per analysis; ops monitor | Product |
| `GQ-02` | Owner of benchmark recalibration | Quarterly review by product, sourced from BCR/SSF/ABANSA | Product |
| `GQ-03` | Web link TTL exact value | 30 days | Product (current default acceptable) |
| `GQ-04` | External project name verification | Not done; report includes a warning | Product (accepted) |
| `GQ-05` | Art. 1686 CC warning policy | `always` for purchase types | Product |
| `GQ-06` | Resend allowed? | Yes, up to 3 resends per analysis, hash-validated | Product |
| `GQ-07` | Repeated analyses idempotency by user | New rubric version → new analysis; same version → return existing | Product |
| `GQ-08` | Error-reporting channel | `errores@casasegura.sv` mailbox | Product |

---

**End of document.**
