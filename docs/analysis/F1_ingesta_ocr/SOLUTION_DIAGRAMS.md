# Solution Diagrams — F1: Ingestion & Text Extraction Pipeline

> Generated: 2026-05-15
> Purpose: Visual validation of the proposed solution using UML notation

---

## 1. Class Diagram (UML)

Structural backbone of F1: every new class, command, query, handler, service, repository, ORM model, and external client introduced. Relationships use UML notation: inheritance (solid line, hollow arrow), composition (filled diamond), dependency (dashed arrow), association (solid line). The diagram is split into two views (domain+application vs. infrastructure) because rendering them together makes the diagram unreadable on a phone screen.

### 1.1 Domain + Application layer

```mermaid
classDiagram
    class ContractSubmission {
        <<Pydantic BaseModel>>
        +UUID|None id
        +str submission_hash
        +str public_short_id
        +int file_count
        +int total_size_bytes
        +int|None total_pages
        +list~str~ file_formats
        +SubmissionSource source
        +dict source_metadata
        +ProcessingStatus processing_status
        +ExtractionStrategy|None extraction_strategy_attempted
        +ExtractionStrategy|None extraction_strategy_successful
        +int|None extracted_text_token_count
        +str|None extracted_text_language
        +float|None extracted_text_language_confidence
        +UUID|None analysis_id
        +datetime disclaimer_accepted_at
        +DisclaimerAcceptanceMethod disclaimer_accepted_via
        +datetime received_at
        +datetime|None processing_started_at
        +datetime|None processing_completed_at
        +datetime expires_at
    }

    class OcrJob {
        <<Pydantic BaseModel>>
        +UUID|None id
        +UUID submission_id
        +ExtractionStrategy strategy
        +int attempt_number
        +str|None model_used
        +datetime started_at
        +datetime|None completed_at
        +OcrJobStatus status
        +int|None pages_processed
        +int|None pages_failed
        +int|None tokens_consumed
        +int|None cost_estimate_cents
        +float|None average_confidence
        +str|None error_code
        +str|None error_message
        +datetime expires_at
    }

    class ExtractedDocument {
        <<Pydantic BaseModel (in-memory only)>>
        +str text
        +ExtractionStrategy strategy_used
        +int pages_processed
        +int pages_failed
        +int tokens_consumed
        +int cost_estimate_cents
    }

    class ProcessingStatus {
        <<StrEnum>>
        RECEIVED
        EXTRACTING
        EXTRACTED
        CLASSIFYING
        ANALYZING
        COMPLETED
        FAILED_EXTRACTION
        FAILED_CLASSIFICATION
        FAILED_ANALYSIS
        REJECTED_LANGUAGE
        REJECTED_TYPE
        REJECTED_SIZE
        EXPIRED
    }

    class ExtractionStrategy {
        <<StrEnum>>
        PYPDF
        VISION_LLM
        TESSERACT
    }

    class SubmissionSource {
        <<StrEnum>>
        WEB
        WHATSAPP
    }

    class OcrJobStatus {
        <<StrEnum>>
        RUNNING
        SUCCESS
        FAILED
        TIMEOUT
        CANCELLED
    }

    class DisclaimerAcceptanceMethod {
        <<StrEnum>>
        WEB_CHECKBOX
        WHATSAPP_REPLY
    }

    class CreateSubmission {
        <<Command>>
        +ContractSubmission submission
    }

    class UpdateSubmissionStatus {
        <<Command>>
        +UUID submission_id
        +ProcessingStatus new_status
        +str|None error_code
        +str|None error_reason
    }

    class CreateOcrJob {
        <<Command>>
        +OcrJob job
    }

    class CompleteOcrJob {
        <<Command>>
        +UUID job_id
        +OcrJobStatus status
        +int|None pages_processed
        +int|None pages_failed
        +int|None tokens_consumed
        +int|None cost_estimate_cents
    }

    class GetSubmissionByPublicShortId {
        <<Query>>
        +str public_short_id
    }

    class GetSubmissionByHash {
        <<Query>>
        +str submission_hash
    }

    class submission_handlers {
        <<handlers>>
        +create_submission(cmd, repo) ContractSubmission
        +update_status(cmd, repo) ContractSubmission
        +get_by_public_short_id(query, repo) ContractSubmission|None
        +get_by_hash(query, repo) ContractSubmission|None
    }

    class ocr_handlers {
        <<handlers>>
        +create_job(cmd, repo) OcrJob
        +complete_job(cmd, repo) OcrJob
    }

    class IngestionService {
        -SubmissionRepository submission_repo
        -OcrJobRepository ocr_repo
        -AnalysisStubRepository analysis_repo
        -ExtractionOrchestrator orchestrator
        -SubmissionQueuePublisher queue_publisher
        +accept_web_submission(payload, files) ContractSubmission
        +accept_whatsapp_files(phone_hash, files, msg_id) ContractSubmission
        +get_status(submission_id_or_short_id) SubmissionStatusView
    }

    class ExtractionOrchestrator {
        -PyPdfExtractor pypdf
        -VisionLlmExtractor vision_llm
        -TesseractExtractor tesseract
        -LanguageDetector lang_detector
        -OcrJobRepository ocr_repo
        +extract(submission, files_in_memory) ExtractedDocument
        -diagnose_strategy(file) ExtractionStrategy
        -run_strategy(strategy, file, attempt) JobResult
        -concatenate_pages(pages) str
        -normalize_text(text) str
    }

    class WhatsAppSessionManager {
        -RedisClient redis
        +start_or_extend(phone_hash, file) WhatsAppSession
        +close(phone_hash, reason) list~FileRef~
        +cancel(phone_hash) None
    }

    ContractSubmission ..> ProcessingStatus
    ContractSubmission ..> ExtractionStrategy
    ContractSubmission ..> SubmissionSource
    ContractSubmission ..> DisclaimerAcceptanceMethod
    OcrJob ..> ExtractionStrategy
    OcrJob ..> OcrJobStatus
    CreateSubmission ..> ContractSubmission
    UpdateSubmissionStatus ..> ProcessingStatus
    CreateOcrJob ..> OcrJob
    CompleteOcrJob ..> OcrJobStatus
    submission_handlers ..> CreateSubmission
    submission_handlers ..> UpdateSubmissionStatus
    submission_handlers ..> GetSubmissionByPublicShortId
    submission_handlers ..> GetSubmissionByHash
    ocr_handlers ..> CreateOcrJob
    ocr_handlers ..> CompleteOcrJob
    IngestionService *-- ExtractionOrchestrator
    IngestionService *-- WhatsAppSessionManager
    IngestionService ..> submission_handlers : calls
    IngestionService ..> ocr_handlers : calls
    ExtractionOrchestrator ..> ExtractedDocument : produces
```

### 1.2 Infrastructure layer

```mermaid
classDiagram
    class ContractSubmissionModel {
        <<Django Model>>
        +UUIDField id
        +TextField submission_hash
        +TextField public_short_id
        +IntegerField file_count
        +BigIntegerField total_size_bytes
        +IntegerField total_pages
        +ArrayField file_formats
        +CharField source
        +JSONField source_metadata
        +CharField processing_status
        +CharField extraction_strategy_attempted
        +CharField extraction_strategy_successful
        +IntegerField extracted_text_token_count
        +CharField extracted_text_language
        +DecimalField extracted_text_language_confidence
        +CharField error_code
        +TextField error_reason
        +UUIDField analysis_id
        +DateTimeField disclaimer_accepted_at
        +CharField disclaimer_accepted_via
        +DateTimeField received_at
        +DateTimeField processing_started_at
        +DateTimeField processing_completed_at
        +DateTimeField expires_at
    }

    class OcrJobModel {
        <<Django Model>>
        +UUIDField id
        +ForeignKey submission
        +CharField strategy
        +IntegerField attempt_number
        +CharField model_used
        +DateTimeField started_at
        +DateTimeField completed_at
        +CharField status
        +IntegerField pages_processed
        +IntegerField pages_failed
        +IntegerField tokens_consumed
        +IntegerField cost_estimate_cents
        +DecimalField average_confidence
        +CharField error_code
        +TextField error_message
        +DateTimeField expires_at
    }

    class ContractSubmissionRepository {
        <<DjangoFullRepository>>
        +to_entity(model) ContractSubmission
        +to_orm_model(entity) SubmissionOrmModel
        +get_by_hash(hash) ContractSubmission|None
        +get_by_public_short_id(short_id) ContractSubmission|None
        +list_in_progress() list~ContractSubmission~
    }

    class OcrJobRepository {
        <<DjangoFullRepository>>
        +to_entity(model) OcrJob
        +to_orm_model(entity) OcrJobOrmModel
        +list_by_submission(submission_id) list~OcrJob~
    }

    class AnalysisStubRepository {
        <<DjangoFullRepository>>
        +create_stub(short_id, submission_hash, channel, target_hash, project_id) UUID
    }

    class PyPdfExtractor {
        <<Strategy>>
        -int timeout_seconds
        -int min_text_chars
        +diagnose(file_bytes) bool
        +extract(file_bytes, submission_id) PageList
    }

    class VisionLlmExtractor {
        <<Strategy>>
        -OpenRouterClient client
        -str model
        -int dpi
        -int max_image_dim_px
        -int timeout_per_page
        -int max_retries_per_page
        -float partial_failure_threshold
        +extract(file_bytes_or_image, submission_id, page_offset) PageList
        -rasterize_pdf(pdf_bytes) list~JpegBytes~
        -build_prompt(page_n, total) ChatMessages
        -call_per_page(image, idempotency_key) str
    }

    class TesseractExtractor {
        <<Strategy>>
        -str language
        -int min_confidence
        -int timeout_per_page
        +extract(file_bytes, submission_id) PageList
        -preprocess(image) Image
    }

    class LanguageDetector {
        +detect(text_sample) tuple~str, float~
    }

    class OpenRouterClient {
        -httpx.Client http
        -str api_key
        -CircuitBreaker breaker
        +chat_completion_vision(model, image, prompt, idempotency_key) str
    }

    class ZavuClient {
        -httpx.Client http
        -str api_key
        -str webhook_secret
        +verify_signature(body, header) bool
        +download_media(signed_url) bytes
        +send_message(to, template, params) None
    }

    class RedisClient {
        -redis.Redis client
        +set_session(key, payload, ttl) None
        +get_session(key) dict|None
        +delete_session(key) None
        +xadd(stream, payload) str
        +xreadgroup(stream, group, consumer) list
    }

    class SubmissionQueuePublisher {
        -RedisClient redis
        -str stream_name
        +publish_extraction_done(envelope) str
    }

    class SubmissionViewSet {
        <<DRF ViewSet>>
        +submit(request) Response
        +status(request, pk) Response
    }

    class ZavuWebhookView {
        <<DRF APIView>>
        +post(request) Response
    }

    class InternalRetryView {
        <<DRF APIView>>
        +post(request, pk) Response
    }

    class ProcessSubmissionTask {
        <<Celery shared_task>>
        +run(submission_id) None
    }

    class MarkStuckSubmissionsTask {
        <<Celery shared_task / Beat>>
        +run() dict
    }

    ContractSubmissionRepository ..> ContractSubmissionModel
    ContractSubmissionRepository ..> ContractSubmission : maps
    OcrJobRepository ..> OcrJobModel
    OcrJobRepository ..> OcrJob : maps
    AnalysisStubRepository ..> UUID
    VisionLlmExtractor *-- OpenRouterClient
    ZavuWebhookView ..> ZavuClient
    SubmissionViewSet ..> IngestionService
    SubmissionQueuePublisher *-- RedisClient
    ProcessSubmissionTask ..> IngestionService
    ProcessSubmissionTask *-- RedisClient
    PyPdfExtractor --|> ExtractionStrategyBase
    VisionLlmExtractor --|> ExtractionStrategyBase
    TesseractExtractor --|> ExtractionStrategyBase
```

---

## 2. Sequence Diagrams (UML)

### 2.1 US-01 — Web upload happy path

```mermaid
sequenceDiagram
    actor User
    participant FE as Web Frontend
    participant View as SubmissionViewSet
    participant Svc as IngestionService
    participant Repo as SubmissionRepository
    participant Stub as AnalysisStubRepository
    participant DB as Postgres
    participant Q as Redis Streams
    participant W as ProcessSubmissionTask
    participant Orch as ExtractionOrchestrator
    participant PyP as PyPdfExtractor
    participant Lang as LanguageDetector

    User->>FE: Picks files, accepts disclaimer, submits
    FE->>View: POST /v1/contracts/submit (multipart, disclaimer_accepted=true, channel, target)
    View->>View: validate file formats, sizes, page caps
    View->>Svc: accept_web_submission(payload, files)
    Svc->>Svc: hash submission (SHA-256 of joined per-file hashes)
    Svc->>Repo: get_by_hash(submission_hash)
    Repo->>DB: SELECT FROM contract_submission ... WHERE submission_hash=$1
    DB-->>Repo: not found
    Repo-->>Svc: None
    Svc->>Stub: create_stub(short_id, hash, channel, target_hash, placeholder_project_id)
    Stub->>DB: INSERT INTO contract_analysis (...)
    DB-->>Stub: analysis_id
    Stub-->>Svc: analysis_id
    Svc->>Repo: save(ContractSubmission(... analysis_id=X, status=RECEIVED))
    Repo->>DB: INSERT INTO contract_submission (...)
    DB-->>Repo: submission_id
    Repo-->>Svc: ContractSubmission
    Svc->>Q: XADD ingestion.submissions {submission_id, in_memory_blob_ref}
    Svc-->>View: ContractSubmission
    View-->>FE: 201 {submission_id, public_short_id, status_url}
    FE-->>User: "Tu análisis está listo en menos de 90s, ID: CS-2026-A1B2C3"

    Q-->>W: XREAD claims the submission
    W->>Svc: mark status=EXTRACTING
    W->>Orch: extract(submission, in_memory_files)
    Orch->>PyP: diagnose(file1)
    PyP-->>Orch: returns True (text-extractable)
    Orch->>PyP: extract(file1)
    PyP->>PyP: pypdf.PdfReader; for each page extract_text(); normalize
    PyP-->>Orch: pages text + token count
    Orch->>Lang: detect(first 2000 chars)
    Lang-->>Orch: ("es", 0.94)
    Orch-->>W: ExtractedDocument(strategy=PYPDF, text=…)
    W->>Repo: update status=EXTRACTED, extracted_text_token_count, language, strategy
    W->>Q: XADD pipeline.classification (envelope F1→F2)
    W->>Svc: discard in-memory file
```

### 2.2 US-06 — Scanned PDF (vision LLM)

```mermaid
sequenceDiagram
    participant Task as ProcessSubmissionTask
    participant Orch as ExtractionOrchestrator
    participant PyP as PyPdfExtractor
    participant Vis as VisionLlmExtractor
    participant Open as OpenRouterClient
    participant CB as CircuitBreaker
    participant OcrR as OcrJobRepository
    participant Lang as LanguageDetector

    Task->>Orch: extract(submission, [scanned_pdf_bytes])
    Orch->>PyP: diagnose(scanned_pdf_bytes)
    PyP-->>Orch: returns False (no text in pypdf probe)
    Orch->>Vis: extract(scanned_pdf_bytes, submission_id)
    Vis->>Vis: rasterize with pdf2image at 150 DPI → 12 JPEGs
    Vis->>OcrR: create_job(strategy=VISION_LLM, model=anthropic/claude-sonnet-4)
    OcrR-->>Vis: job_id
    loop For each page (1..12)
        Vis->>CB: allow?
        alt Circuit closed
            CB-->>Vis: yes
            Vis->>Open: chat_completion_vision(image, prompt, key=submission:p1:vision_llm:1)
            Open-->>Vis: transcribed text or error
        else Circuit open
            CB-->>Vis: NO
            Vis->>Vis: skip remaining LLM calls, escalate to fallback
        end
        Vis->>Vis: if error: backoff 1s, 4s; max 2 retries
        Vis->>Vis: track tokens + cost
    end
    Vis->>OcrR: complete_job(status=SUCCESS|FAILED, tokens, cost, pages_processed, pages_failed)
    alt success rate > 70%
        Vis-->>Orch: ExtractedDocument(strategy=VISION_LLM, …)
        Orch->>Lang: detect(text)
        Lang-->>Orch: ("es", 0.91)
        Orch-->>Task: ExtractedDocument
    else success rate ≤ 70%
        Vis-->>Orch: PartialFailure
        Orch->>Orch: escalate to TesseractExtractor (if OCR_TESSERACT_ENABLED)
    end
```

### 2.3 US-02 — WhatsApp multi-file session

```mermaid
sequenceDiagram
    actor U as User (WhatsApp)
    participant Zavu as Zavu
    participant ZW as ZavuWebhookView
    participant Sess as WhatsAppSessionManager
    participant Redis as Redis
    participant Svc as IngestionService

    U->>Zavu: sends photo of page 1
    Zavu->>ZW: POST /v1/zavu/webhook (signed)
    ZW->>ZW: verify HMAC signature
    ZW->>Sess: start_or_extend(phone_hash, file_ref_1)
    Sess->>Redis: GET whatsapp_session:phone_hash
    Redis-->>Sess: nil
    Sess->>Redis: SET ... (TTL 300s) with [file_ref_1]
    Sess->>ZW: NewSession
    ZW->>Zavu: send welcome+disclaimer ("acepto?")
    Zavu->>U: shows message
    U->>Zavu: "acepto"
    Zavu->>ZW: webhook (text "acepto")
    ZW->>Sess: mark_disclaimer_accepted(phone_hash)
    U->>Zavu: sends photo of page 2
    Zavu->>ZW: webhook (media)
    ZW->>Sess: start_or_extend(phone_hash, file_ref_2)
    Sess->>Redis: EXPIRE 300 + append file_ref_2
    U->>Zavu: writes "listo"
    Zavu->>ZW: webhook (text "listo")
    ZW->>Sess: close(phone_hash, reason=user_done)
    Sess->>Redis: GET ... payload
    Redis-->>Sess: [file_ref_1, file_ref_2]
    Sess->>Redis: DEL whatsapp_session:phone_hash
    ZW->>Svc: accept_whatsapp_files(phone_hash, [refs], msg_id)
    Svc->>Svc: download files via signed URLs (in memory)
    Svc->>Svc: hash, validate, dedupe, stub analysis, create submission
    Svc-->>ZW: ContractSubmission
    ZW->>Zavu: send "Estoy analizando… te aviso en menos de 2 min."
```

### 2.4 US-03 — Deduplication on resubmission

```mermaid
sequenceDiagram
    actor User
    participant View as SubmissionViewSet
    participant Svc as IngestionService
    participant Repo as SubmissionRepository

    User->>View: POST /v1/contracts/submit (same bytes as before)
    View->>Svc: accept_web_submission
    Svc->>Svc: hash → 0xDEAD…
    Svc->>Repo: get_existing_analysis_by_hash(0xDEAD…)
    Repo-->>Svc: ContractAnalysis(id=ABC, public_short_id=CS-2026-PREV, anonymized=False, rubric_version=v1)
    Svc->>Svc: compare active rubric_version
    alt Same version
        Svc-->>View: DuplicateResult(analysis_id=ABC, short_id=CS-2026-PREV)
        View-->>User: 409 {is_duplicate=true, analysis_id, public_short_id}
    else Different version
        Svc->>Svc: create new ContractSubmission + new stub ContractAnalysis
        Svc-->>View: NewSubmissionResult
        View-->>User: 201 normal flow
    end
```

### 2.5 Error path — Language not Spanish

```mermaid
sequenceDiagram
    participant Orch as ExtractionOrchestrator
    participant Lang as LanguageDetector
    participant Repo as SubmissionRepository
    participant DB as Postgres
    participant Q as Redis Streams

    Orch->>Lang: detect(text)
    Lang-->>Orch: ("en", 0.92)
    Orch->>Repo: update status=REJECTED_LANGUAGE, error_code=LANGUAGE_NOT_SUPPORTED
    Repo->>DB: UPDATE contract_submission SET ...
    DB-->>Repo: ok
    Orch->>Orch: discard extracted text + in-memory file
    Note over Orch,Q: No publication to F2 queue. The status endpoint will return rejected_language on next poll.
```

---

## 3. State Diagram — Submission processing

```mermaid
stateDiagram-v2
    [*] --> received
    received --> extracting: worker picks
    extracting --> extracted: text ok + lang ok
    extracting --> failed_extraction: all strategies failed OR text too short
    extracting --> rejected_language: lang ≠ es
    extracted --> classifying: F2 picked up
    classifying --> analyzing: F2 done
    analyzing --> completed: F4+F5+F6 done
    received --> expired: stuck > 1h
    extracting --> expired: stuck > 1h
    failed_extraction --> [*]: 24h TTL hard delete (F8)
    rejected_language --> [*]: 24h TTL hard delete (F8)
    expired --> [*]: 24h TTL hard delete (F8)
    completed --> [*]: 24h TTL hard delete (F8, analysis_id preserved separately)
```

---

## 4. Activity Diagram — Strategy routing & extraction

```mermaid
flowchart TD
    A[Start: file arrives in submission] --> B{format?}
    B -->|PDF| C{pypdf probe page 1 returns more than 100 chars?}
    B -->|image jpg, png, heic, webp| F[strategy = VISION_LLM]
    C -->|yes| D[strategy = PYPDF]
    C -->|no| E[strategy = VISION_LLM]
    D --> G[Run pypdf for all pages]
    G --> H{text greater than or equal 500 chars after normalization?}
    H -->|yes| Z1[Pass to language detection]
    H -->|no| E
    E --> I[Rasterize PDF at 150 DPI to JPEGs]
    F --> J[Convert HEIC and WEBP to JPEG, clamp dims to 1920px]
    I --> K[Call OpenRouter per page with idempotency key]
    J --> K
    K --> L{per-page success?}
    L -->|yes| M[Append page text]
    L -->|transient err| N[Backoff and retry up to 2 times]
    N --> K
    L -->|permanent err| O[Mark page failed]
    M --> P{all pages done?}
    O --> P
    P -->|no| K
    P -->|yes| Q{failed pages over 30 percent?}
    Q -->|no| Z1
    Q -->|yes and TESSERACT_ENABLED| R[Run Tesseract fallback for failed pages]
    Q -->|yes and not enabled| S[Mark failed_extraction and stop]
    R --> T{Tesseract avg confidence over 60?}
    T -->|yes| Z1
    T -->|no| S
    Z1{Language is es with confidence over 0.85?} --> U[Mark status = EXTRACTED, publish to F2 queue]
    Z1 -->|no| V[Mark status = REJECTED_LANGUAGE, stop]
    S --> X[Terminal]
    U --> X
    V --> X
```

---

## 5. Component Diagram

```mermaid
graph TD
    subgraph Client
        WebFE[Next.js Web Frontend]
        WhatsAppUser[WhatsApp User]
    end

    subgraph "External services"
        Zavu[Zavu WhatsApp API]
        OpenRouter[OpenRouter LLM Gateway]
    end

    subgraph "Casa Segura API (Django + DRF)"
        SubViewSet[SubmissionViewSet]
        ZavuWh[ZavuWebhookView]
        InternalView[InternalRetryView]
    end

    subgraph "Application: ingestion module"
        IngSvc[IngestionService]
        WaSess[WhatsAppSessionManager]
        Orch[ExtractionOrchestrator]
    end

    subgraph "Infrastructure"
        PyP[PyPdfExtractor]
        Vis[VisionLlmExtractor]
        Tess[TesseractExtractor]
        Lang[LanguageDetector]
        OpenClient[OpenRouterClient]
        ZavuClient[ZavuClient]
        RedisClient[RedisClient]
        SubRepo[SubmissionRepository]
        OcrRepo[OcrJobRepository]
        StubRepo[AnalysisStubRepository]
    end

    subgraph "Celery workers"
        IngWorker["process_submission task"]
        StuckBeat["mark_stuck_submissions (Beat)"]
        WaListener["WhatsApp session listener (daemon)"]
    end

    subgraph "Stores"
        PG[(Postgres)]
        Redis[(Redis)]
    end

    WebFE -->|HTTPS| SubViewSet
    WebFE -->|HTTPS poll| SubViewSet
    WhatsAppUser -->|WhatsApp| Zavu
    Zavu -->|HTTPS webhook| ZavuWh
    SubViewSet --> IngSvc
    ZavuWh --> WaSess
    ZavuWh --> IngSvc
    WaSess --> RedisClient
    IngSvc --> SubRepo
    IngSvc --> OcrRepo
    IngSvc --> StubRepo
    IngSvc --> Orch
    Orch --> PyP
    Orch --> Vis
    Orch --> Tess
    Orch --> Lang
    Vis --> OpenClient
    Tess -.uses.-> TesseractBinary[Tesseract OS binary]
    OpenClient -->|HTTPS| OpenRouter
    ZavuClient -->|HTTPS| Zavu
    IngWorker --> IngSvc
    IngWorker --> RedisClient
    SubRepo --> PG
    OcrRepo --> PG
    StubRepo --> PG
    RedisClient --> Redis
    IngSvc -->|publish XADD| Redis
```

---

## 6. Use Case Diagram

Casa Segura has no user accounts; the actors are roles, not authenticated users.

```mermaid
graph LR
    subgraph Actors
        Anon[Anonymous user — web]
        WaUser[Anonymous user — WhatsApp]
        Zavu[Zavu webhook system]
        Op[Internal operator]
    end

    subgraph "F1 Use Cases"
        UC1((Submit contract from web))
        UC2((Send contract via WhatsApp))
        UC3((Poll submission status))
        UC4((Receive Zavu media))
        UC5((Inspect failed submissions))
    end

    Anon --> UC1
    Anon --> UC3
    WaUser --> UC2
    Zavu --> UC4
    Op --> UC5
```

---

## Notes

- The class diagram uses two views to remain readable. In the implementation, both layers exist together.
- `ExtractionStrategyBase` is the implicit interface every extractor satisfies (`extract(file, submission_id) -> PageList` and `diagnose(file) -> bool`). It is a Python `Protocol` (structural typing), not a concrete base class.
- The circuit breaker is not shown as a separate class in §1.1 because it is a wrapper at the `OpenRouterClient` level; conceptually it is part of `VisionLlmExtractor`'s resilience strategy.
- Idempotency keys for OpenRouter calls follow the format `submission_id:page_number:strategy:attempt_number`, as mandated by `PRD_F1` BR-05.
- All diagrams are intentionally limited to F1 boundaries. F2/F3/F4 interactions appear as "out arrows" only.

**End of document.**
