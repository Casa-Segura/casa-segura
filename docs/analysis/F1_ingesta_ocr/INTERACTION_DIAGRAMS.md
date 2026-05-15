# Interaction Diagrams — F1: Ingestion & Text Extraction Pipeline

> Generated: 2026-05-15
> Companion to `SOLUTION_DIAGRAMS.md`. The diagrams below focus on **inter-component** flows (across modules and external systems) rather than the structural class views in SOLUTION_DIAGRAMS.

---

## Component Overview

```mermaid
graph TD
    subgraph "Browser / WhatsApp"
        Web[Next.js Web]
        Wa[WhatsApp]
    end

    subgraph "F1 module — Casa Segura"
        Router[DRF ViewSets + APIViews]
        Svc[IngestionService]
        Sess[WhatsAppSessionManager]
        Orch[ExtractionOrchestrator]
        Workers[Celery: process_submission task]
        Beat[Celery Beat: mark_stuck_submissions]
        Listener[Redis keyspace listener: WhatsApp sessions]
    end

    subgraph "Adapters"
        OrAdapter[OpenRouter adapter]
        ZavuAdapter[Zavu adapter]
        TessBin[Tesseract OS binary]
        PyPdfLib[pypdf library]
    end

    subgraph "Infra"
        PG[(Postgres)]
        Redis[(Redis)]
    end

    subgraph "Downstream"
        F2[F2 Classification worker]
        F8Cron[F8 cron jobs]
    end

    Web -->|multipart| Router
    Wa --> ZavuAdapter
    ZavuAdapter -->|webhook| Router
    Router --> Svc
    Router --> Sess
    Sess --> Redis
    Svc --> PG
    Svc -->|XADD ingestion.submissions| Redis
    Workers -->|XREAD| Redis
    Workers --> Svc
    Workers --> Orch
    Orch --> PyPdfLib
    Orch --> OrAdapter
    Orch --> TessBin
    OrAdapter -->|HTTPS| OpenRouter[(OpenRouter)]
    Workers -->|XADD pipeline.classification| Redis
    F2 -->|XREAD| Redis
    F8Cron --> PG
```

---

## Flow: US-01 Web upload — happy path

### Sequence Diagram — Happy Path

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Web Frontend
    participant V as SubmissionViewSet
    participant V as Validator
    participant S as IngestionService
    participant Repo as SubmissionRepository
    participant Stub as AnalysisStubRepository
    participant PG as Postgres
    participant Q as Redis Streams
    participant W as ProcessSubmissionTask
    participant O as ExtractionOrchestrator
    participant Lang as LanguageDetector

    U->>FE: pick files + accept disclaimer + submit
    FE->>R: POST /v1/contracts/submit (multipart)
    R->>V: validate(payload, files)
    V-->>R: ok
    R->>S: accept_web_submission(payload)
    S->>S: hash files, compute submission_hash
    S->>Repo: get_existing_analysis_by_hash(...)
    Repo->>PG: SELECT ...
    PG-->>Repo: not found
    Repo-->>S: None
    S->>Stub: create_stub(short_id, hash, channel, target_hash, placeholder_project_id)
    Stub->>PG: INSERT contract_analysis
    PG-->>Stub: analysis_id
    S->>Repo: save(ContractSubmission(...))
    Repo->>PG: INSERT contract_submission
    PG-->>Repo: ok
    S->>Q: XADD ingestion.submissions
    S-->>R: SubmissionAcceptedView
    R-->>FE: 201 {submission_id, public_short_id, status_url}
    Q-->>W: XREADGROUP
    W->>S: mark_extracting(submission_id)
    W->>O: extract(submission, files_in_memory)
    O->>O: diagnose + run strategy
    O->>Lang: detect(text)
    Lang-->>O: ("es", 0.94)
    O-->>W: ExtractedDocument
    W->>Repo: update status=EXTRACTED, language, token_count, strategy
    W->>Q: XADD pipeline.classification {ExtractionDone envelope}
    W->>W: discard in-memory files
```

### Sequence Diagram — Validation error (FORMAT_NOT_SUPPORTED)

```mermaid
sequenceDiagram
    actor U as User
    participant FE as Web Frontend
    participant V as SubmissionViewSet
    participant V as Validator

    U->>FE: pick a .docx by mistake
    FE->>R: POST /v1/contracts/submit (multipart, contains .docx)
    R->>V: validate(payload, files)
    V-->>R: error FORMAT_NOT_SUPPORTED on contract.docx
    R-->>FE: 400 {code: "FORMAT_NOT_SUPPORTED", details: {rejected_files: ["contract.docx"]}}
    FE-->>U: "Solo aceptamos PDF, JPG, PNG, HEIC, WEBP"
```

---

## Flow: US-02 WhatsApp — multi-message session

### Sequence Diagram — Happy Path

```mermaid
sequenceDiagram
    actor U as User (WhatsApp)
    participant Z as Zavu
    participant Whv as ZavuWebhookView
    participant Sig as SignatureVerifier
    participant Sess as WhatsAppSessionManager
    participant R as Redis
    participant S as IngestionService

    U->>Z: photo of page 1
    Z->>Whv: POST /v1/zavu/webhook (signed)
    Whv->>Sig: verify(body, X-Zavu-Signature)
    Sig-->>Whv: ok
    Whv->>Sess: start_or_extend(phone_hash, file_ref_1)
    Sess->>R: GET whatsapp_session:HASH
    R-->>Sess: nil
    Sess->>R: SETEX whatsapp_session:HASH 300 {disclaimer_accepted: false, files:[ref1]}
    Sess-->>Whv: NEW_SESSION
    Whv->>Z: send welcome + disclaimer "Responde acepto"
    Z->>U: shows welcome
    U->>Z: "acepto"
    Z->>Whv: POST webhook (text "acepto")
    Whv->>Sess: mark_disclaimer_accepted(phone_hash)
    Sess->>R: HSET ... disclaimer_accepted=true
    U->>Z: photo of page 2
    Z->>Whv: POST webhook (media)
    Whv->>Sess: start_or_extend(phone_hash, file_ref_2)
    Sess->>R: EXPIRE 300 + append file_ref_2
    U->>Z: "listo"
    Z->>Whv: POST webhook (text "listo")
    Whv->>Sess: close(phone_hash, reason=user_done)
    Sess->>R: GET ... → payload
    Sess->>R: DEL whatsapp_session:HASH
    Sess-->>Whv: payload {files:[ref1, ref2], disclaimer_accepted_at: ts}
    Whv->>S: accept_whatsapp_files(phone_hash, files, msg_id, disclaimer_ts)
    S->>S: download via signed URLs (in memory only)
    S->>S: hash + validate + dedupe + create stub + create submission
    S-->>Whv: ContractSubmission
    Whv->>Z: send "Estoy analizando…"
```

### Sequence Diagram — Session timeout without "listo"

```mermaid
sequenceDiagram
    actor U as User (WhatsApp)
    participant Z as Zavu
    participant Listener as SessionExpiryListener
    participant Sess as WhatsAppSessionManager
    participant S as IngestionService

    U->>Z: photo of page 1
    Note over U: 5 minutes pass with no "listo" and no further pages
    Listener->>Listener: receives Redis KEYSPACE expired event for whatsapp_session:HASH
    Listener->>Sess: handle_timeout(phone_hash)
    Sess->>Sess: read final payload from a separate dead-letter key (set by SETEX BEFORE expiration)
    alt session had files + disclaimer
        Sess->>S: accept_whatsapp_files(phone_hash, files, timeout_reason)
        S-->>Z: send "Procesando tu contrato (cerré sesión por inactividad)"
    else session had files but no disclaimer
        Sess->>Z: send "No recibí tu confirmación de acepto. Si quieres analizar tu contrato, mándalo de nuevo y responde acepto."
        Sess->>Sess: discard files
    end
```

(Note: Redis keyspace notifications require enabling `notify-keyspace-events Ex` in the Redis config; documented in `IMPLEMENTATION_PLAN.md`.)

---

## Flow: US-03 Deduplication on hash collision

### Sequence Diagram

```mermaid
sequenceDiagram
    actor U as User
    participant V as SubmissionViewSet
    participant S as IngestionService
    participant Repo as SubmissionRepository
    participant PG as Postgres
    participant RV as RubricVersionService

    U->>R: POST /v1/contracts/submit (same bytes as prior)
    R->>S: accept_web_submission
    S->>S: compute submission_hash (same as prior)
    S->>Repo: get_completed_analysis_by_hash(hash)
    Repo->>PG: SELECT ContractAnalysis ... WHERE submission_hash=$1 AND anonymized_at IS NULL
    PG-->>Repo: ContractAnalysis(id=A, rubric_version=v1)
    Repo-->>S: ContractAnalysis A
    S->>RV: active_rubric_version()
    RV-->>S: v1
    alt v1 == A.rubric_version
        S-->>R: DuplicateResult(analysis_id=A, short_id=A.short_id)
        R-->>U: 409 {is_duplicate=true, ...}
    else version differs
        S->>S: create a new ContractSubmission + new stub ContractAnalysis
        S-->>R: NewSubmissionResult
        R-->>U: 201 normal
    end
```

---

## Flow: US-06 Vision LLM extraction

### Sequence Diagram

```mermaid
sequenceDiagram
    participant W as ProcessSubmissionTask
    participant O as ExtractionOrchestrator
    participant P as PyPdfExtractor
    participant V as VisionLlmExtractor
    participant Raster as pdf2image
    participant Repo as OcrJobRepository
    participant CB as CircuitBreaker
    participant C as OpenRouterClient
    participant OR as OpenRouter
    participant L as LanguageDetector

    W->>O: extract(submission, file_bytes)
    O->>P: diagnose(file_bytes)
    P-->>O: False (no extractable text on page 1)
    O->>V: extract(file_bytes, submission_id)
    V->>Raster: pdf to JPEGs at 150 DPI
    Raster-->>V: 12 images
    V->>Repo: create_job(strategy=vision_llm, model=anthropic/claude-sonnet-4, attempt=1)
    Repo-->>V: job_id
    loop per page
        V->>CB: allow?
        CB-->>V: yes (closed)
        V->>C: chat_completion_vision(model, image, prompt, idempotency_key=submission:p{n}:vision_llm:1)
        C->>OR: POST /chat/completions
        OR-->>C: 200 transcribed text
        C-->>V: text
        V->>V: track tokens & cost
    end
    V->>Repo: complete_job(status=success, pages_processed=12, tokens, cost)
    V-->>O: text
    O->>L: detect(text)
    L-->>O: ("es", 0.91)
    O-->>W: ExtractedDocument(strategy=vision_llm, ...)
```

### Sequence Diagram — Vision partial failure + Tesseract fallback

```mermaid
sequenceDiagram
    participant V as VisionLlmExtractor
    participant CB as CircuitBreaker
    participant C as OpenRouterClient
    participant T as TesseractExtractor
    participant O as ExtractionOrchestrator
    participant Repo as OcrJobRepository

    V->>C: page 5 chat_completion_vision
    C-->>V: 503 (transient)
    V->>V: backoff 1s
    V->>C: retry attempt 2 (same idempotency key)
    C-->>V: 503
    V->>V: backoff 4s
    V->>C: retry attempt 3 (max)
    C-->>V: 503
    V->>V: mark page 5 failed; continue to page 6
    Note over V: 4 of 12 pages failed → 33% > threshold 30%
    V->>Repo: complete_job(status=failed, pages_failed=4, ...)
    V-->>O: PartialFailure(pages_failed=4)
    O->>O: OCR_TESSERACT_ENABLED → yes
    O->>T: extract(file_bytes, submission_id, only_pages=[5,7,9,12])
    T->>Repo: create_job(strategy=tesseract, attempt=1)
    Repo-->>T: job_id
    T->>T: pytesseract for each failed page
    T->>Repo: complete_job(status=success or failed)
    alt all pages OK and avg confidence >= 60
        T-->>O: merged text
        O->>O: stitch with vision_llm partial result
    else
        T-->>O: TesseractFailed
        O->>O: mark submission failed_extraction
    end
```

---

## Class Diagram

```mermaid
classDiagram
    class ContractSubmission {
        <<Pydantic>>
    }
    class OcrJob {
        <<Pydantic>>
    }
    class ExtractedDocument {
        <<Pydantic in-memory only>>
    }
    class IngestionService {
        +accept_web_submission()
        +accept_whatsapp_files()
        +get_status()
    }
    class ExtractionOrchestrator {
        +extract()
    }
    class WhatsAppSessionManager {
        +start_or_extend()
        +close()
        +cancel()
    }
    class ExtractionStrategyBase {
        <<Protocol>>
        +diagnose(file) bool
        +extract(file, submission_id) PageList
    }
    class PyPdfExtractor
    class VisionLlmExtractor
    class TesseractExtractor
    class LanguageDetector {
        +detect(text)
    }
    class SubmissionRepository {
        +save() get_by_hash() get_by_public_short_id()
    }
    class OcrJobRepository
    class AnalysisStubRepository
    class OpenRouterClient
    class ZavuClient
    class RedisClient
    class SubmissionQueuePublisher
    class ProcessSubmissionTask

    IngestionService *-- ExtractionOrchestrator
    IngestionService *-- WhatsAppSessionManager
    IngestionService o-- SubmissionRepository
    IngestionService o-- OcrJobRepository
    IngestionService o-- AnalysisStubRepository
    IngestionService o-- SubmissionQueuePublisher
    ExtractionOrchestrator o-- PyPdfExtractor
    ExtractionOrchestrator o-- VisionLlmExtractor
    ExtractionOrchestrator o-- TesseractExtractor
    ExtractionOrchestrator o-- LanguageDetector
    PyPdfExtractor ..|> ExtractionStrategyBase
    VisionLlmExtractor ..|> ExtractionStrategyBase
    TesseractExtractor ..|> ExtractionStrategyBase
    VisionLlmExtractor *-- OpenRouterClient
    WhatsAppSessionManager o-- RedisClient
    SubmissionQueuePublisher *-- RedisClient
    ProcessSubmissionTask o-- IngestionService
```

---

## Notes

- All extractors are wrapped by per-page timeouts (`OCR_VISION_TIMEOUT_PER_PAGE_SECONDS`, `OCR_TESSERACT_TIMEOUT_PER_PAGE_SECONDS`). Timeouts bubble as `JobResult(status=TIMEOUT)` and are noted in `OcrJob` without aborting the whole submission unless they cross the partial-failure threshold.
- The `process_submission` Celery task runs in the standard Celery worker pool. Concurrency is controlled by `CELERY_WORKER_CONCURRENCY` (default 4); each task processes one `submission_id` end-to-end. The worker process holds the in-memory file bytes only as long as the task is running; the Redis blob key with the original bytes has TTL ≤ 300 s and is explicitly `DEL`'d in `finally`.
- The Redis keyspace notification needed for WhatsApp session timeout requires `notify-keyspace-events Ex` set in `redis.conf` or via `CONFIG SET`.
- `LanguageDetector` is intentionally a thin wrapper; the dependency (`langdetect` or `lingua-py`) is chosen at module-load time based on `OCR_LANGUAGE_DETECTOR` env var (default `langdetect`).
- `OpenRouterClient` exposes one public method (`chat_completion_vision`). The decision to log `extra={"cost_cents": ..., "tokens": ...}` happens inside the client, so the orchestrator does not need to know per-model pricing.

**End of document.**
