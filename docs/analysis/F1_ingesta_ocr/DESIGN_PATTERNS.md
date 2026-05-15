# Design Patterns — F1: Ingestion & Text Extraction Pipeline

> Generated: 2026-05-15
> Cross-cutting patterns shared across the whole product live in `../_shared/GLOBAL_ASSUMPTIONS.md` §12. This file adds only patterns specific to F1.

---

## Patterns Applied

### Strategy

**Why this pattern fits:** F1 has three concrete extraction techniques (`pypdf`, `vision_llm`, `tesseract`) that are interchangeable behind one interface: "give me text from this file". The PRD lists explicit routing rules (BR-04 and US-04/05/06/07): which strategy to try first, when to escalate. Each strategy has its own latency, cost, dependencies, and failure modes. Encoding them as classes implementing a `Protocol` keeps the orchestrator readable and makes it trivial to add a fourth strategy (e.g., AWS Textract) later without touching `IngestionService`.

**What it covers:**
- `PyPdfExtractor`, `VisionLlmExtractor`, `TesseractExtractor` — each in `ingestion/infrastructure/ocr/{name}_extractor.py`
- Common `Protocol` `ExtractionStrategy` (PEP 544) with two methods: `diagnose(file) -> bool` and `extract(file, submission_id) -> PageList`
- `ExtractionOrchestrator` consumes the protocol; it does not know which class it is calling

**What it does NOT cover:**
- The decision of *which* strategy to use first is not in the strategy itself; that lives in `ExtractionOrchestrator.diagnose_strategy()` (a small piece of routing logic with config knobs `OCR_COST_SAVER_MODE` etc.). Each strategy only reports whether it can probably succeed.
- Cost tracking is also outside the protocol; each strategy reports its tokens/cost in the result object, and the orchestrator persists the `OcrJob`.

**Implementation location:**
- `ingestion/infrastructure/ocr/base.py` — the `Protocol`
- `ingestion/infrastructure/ocr/pypdf_extractor.py`
- `ingestion/infrastructure/ocr/vision_llm_extractor.py`
- `ingestion/infrastructure/ocr/tesseract_extractor.py`
- Orchestration in `ingestion/application/services/ingestion_service.py` via `ExtractionOrchestrator`

---

### Pipeline / Pipes & Filters

**Why this pattern fits:** Casa Segura's whole product is a linear pipeline (`F1 → F2 → F4+F5 → F6 → F7`). Each stage's output is the next stage's input, and stages communicate over a queue (Redis Streams) rather than direct calls. F1 is the first stage. By treating the queue boundary explicitly, F1 stays decoupled: it doesn't even know what F2 will do with its output, beyond the contract published in `_shared/GLOBAL_ASSUMPTIONS.md` §13.

**What it covers:**
- The `XADD pipeline.classification {envelope}` publication at the end of successful extraction
- The envelope shape `ExtractionDone` (in `ingestion/application/contracts/messages.py`)
- The `process_submission` Celery task consuming the F1 submit signal and publishing to `ingestion.to_classification` after extraction completes

**What it does NOT cover:**
- The semantics of the message *content* (that is owned by F2's consumer; F1 only owns the envelope shape it publishes).
- Delivery guarantees: Redis Streams gives at-least-once; the consumer (F2) deduplicates by `submission_id`. F1 idempotency relies on `submission_hash`.

**Implementation location:**
- `ingestion/infrastructure/queue/publisher.py` (`SubmissionQueuePublisher`)
- `ingestion/infrastructure/celery/ingestion_tasks.py` (`process_submission` Celery task) plus `ingestion/infrastructure/redis/stream_publisher.py` (`SubmissionStreamPublisher` writing the F1→F2 envelope)
- `ingestion/application/contracts/messages.py` (Pydantic envelopes)

---

### Circuit breaker

**Why this pattern fits:** F1 makes potentially many vision-LLM calls per submission (one per page of a scanned PDF). The PRD's NFR section (§9) says: "circuit breaker opens after 5 consecutive failures in 60 seconds, recovers after 5 minutes; when open, new submissions use Tesseract directly". This is operationally critical — without it, an OpenRouter outage cascades into 5-minute submission timeouts and a flood of failed jobs.

**What it covers:**
- A `CircuitBreaker` wrapper around `OpenRouterClient.chat_completion_vision(...)`
- Three states: `closed` (calls flow), `open` (calls fail-fast), `half-open` (a probe call decides whether to close again)
- Failure counter window of 60 seconds, breaker open duration of 5 minutes

**What it does NOT cover:**
- Per-page transient retries (handled inside `VisionLlmExtractor` with exponential backoff 1 s, 4 s, max 2 retries). The circuit breaker fires *after* those retries.
- The actual fallback decision to Tesseract — that lives in `ExtractionOrchestrator`.

**Implementation location:**
- `shared/infrastructure/resilience/circuit_breaker.py` (the reusable class)
- `ingestion/infrastructure/llm/openrouter_client.py` (uses the breaker)
- Configuration: `OPENROUTER_CB_FAILURE_THRESHOLD=5`, `OPENROUTER_CB_TIME_WINDOW_SECONDS=60`, `OPENROUTER_CB_OPEN_DURATION_SECONDS=300`

---

### Idempotency key (request deduplication)

**Why this pattern fits:** Two motivations. (1) OpenRouter HTTP retries (network reset, 5xx) must not double-bill — the PRD demands an idempotency key per page. (2) The user accidentally clicking "Submit" twice in the browser must yield the same `analysis_id`, not two separate analyses.

**What it covers:**
- LLM-call idempotency: header `Idempotency-Key: {submission_id}:p{page_n}:vision_llm:a{attempt}` on every OpenRouter call (the spec supports it; OpenAI-compatible providers also do).
- Submission-level idempotency: `submission_hash` is the deduplication key against `ContractSubmission.submission_hash` and `ContractAnalysis.submission_hash`. The deduplication query is run before any worker is invoked.

**What it does NOT cover:**
- LLM responses that legitimately differ on retry (e.g., the model returns different transcriptions). The system trusts the first successful response and discards retry attempts that arrive late.
- User-facing "retry" buttons in the frontend — those are out of F1's scope.

**Implementation location:**
- `ingestion/application/services/ingestion_service.py::_check_idempotency()`
- `ingestion/infrastructure/llm/openrouter_client.py::chat_completion_vision()`

---

### Capability token

**Why this pattern fits:** The user has no account. They receive a `public_short_id` (e.g. `CS-2026-A1B2C3`) when they upload. That ID is the only credential the user holds: it lets them poll status (read-only) and later request resends (paired with destination hash check). The entropy of the short ID is high enough that guessing is infeasible (30+ bits in the 6-char suffix), satisfying PRD F7 BR-07.

**What it covers:**
- Generation of `public_short_id` with `base32`-encoded random bytes
- The `GET /v1/contracts/{submission_id_or_short_id}/status` endpoint accepting both IDs interchangeably (the path-parameter lookup tries UUID first, then short ID)
- No authentication header required on the status endpoint

**What it does NOT cover:**
- The destination-hash check on resend (that is F7, the pattern is the same)
- The Zavu webhook signature (HMAC of body, a different concern)

**Implementation location:**
- `ingestion/application/services/short_id_generator.py`
- `ingestion/infrastructure/django/views.py::SubmissionViewSet`

---

### Session (transient state in Redis)

**Why this pattern fits:** WhatsApp's natural interaction is conversational and asynchronous: pages arrive one at a time over up to five minutes. The system must accumulate them, time them out, and close the session cleanly. Storing this in Postgres would be a poor fit (many writes, short life). Redis with a TTL of 300 s is the canonical solution.

**What it covers:**
- `WhatsAppSessionManager` with `start_or_extend`, `close`, `cancel`
- Redis key format: `whatsapp_session:{phone_hash}`
- Session payload: `{"phone_hash": "...", "disclaimer_accepted": bool, "files": [...], "started_at": ts, "msg_count": int}`
- Auto-close on TTL expiration (Redis keyspace notification subscription in the worker)

**What it does NOT cover:**
- The actual download of media files from Zavu signed URLs (that is `ZavuClient.download_media()`)
- The hashing of the phone number (done with salt+SHA-256 at the `ZavuWebhookView` boundary)

**Implementation location:**
- `ingestion/application/services/whatsapp_session.py`
- `ingestion/infrastructure/redis/session_store.py`

---

### Stub-then-fill (delayed back-fill)

**Why this pattern fits:** The PRD requires that the user receive `public_short_id` in the upload response (latency: under one second). But the `ContractAnalysis` row's `project_id` cannot be known until F2 has classified the contract and extracted the name. The stub-then-fill pattern resolves this: F1 inserts a partial `ContractAnalysis` row with `project_id = <placeholder>` and the columns it can populate (hash, short id, delivery channel, target hash, link expiration). F2 later runs `UPDATE contract_analysis SET project_id = ... WHERE id = ...`.

**What it covers:**
- `AnalysisStubRepository.create_stub(...)` invoked from `IngestionService`
- A seeded `project` row `__unknown_pending__` (`metadata.placeholder=true`) that satisfies the `NOT NULL` FK constraint until F2 updates it
- A small migration safeguard: a trigger on `contract_analysis` that rejects inserts pointing to the placeholder project unless the row has `processing_status` indicating mid-flow (this would prevent a runaway bug from leaving placeholder-orphan analyses)

**What it does NOT cover:**
- F2's logic to update `project_id` (owned by F2)
- The cleanup of orphan stubs whose F2 step never ran (owned by F8's `expire_links` / abandonment cron, which catches this through the parent `ContractSubmission` going `expired`)

**Implementation location:**
- `ingestion/infrastructure/db/repositories.py::AnalysisStubRepository`
- `platform/infrastructure/db/migrations/0001_initial.py` (the seed insertion of the placeholder project)

---

## Patterns Considered and Rejected

### Saga / orchestrator with compensating actions

Was the right pattern if extraction or stub creation needed strong transactional consistency across multiple external services. F1 only has one external dependency for writes (Postgres) and one for reads (OpenRouter); a saga would be overkill. Compensating actions for OpenRouter (a "refund" call) do not exist. The current design tolerates LLM-call costs that complete without being used (e.g., when extraction succeeds but language detection fails) — they are logged but irrecoverable. A saga would not change that.

### Event sourcing on `ContractSubmission`

Was the right pattern if we needed an audit trail of every state transition. The PRD's audit requirements are simpler: state transitions are logged structurally, and `OcrJob` already provides per-strategy observability. The added complexity of an event log table without a strong need (regulatory or analytical) is not justified at MVP.

### Long-running synchronous request

Naive option: `POST /v1/contracts/submit` blocks until the analysis finishes and returns the report. Rejected because: (a) the P95 target is 90 s while typical web request timeouts are 30–60 s; (b) the user often closes the tab; (c) WhatsApp is intrinsically asynchronous and a single design must serve both channels. The current design uses a status endpoint the frontend polls, plus eventual delivery via the chosen channel.

### Per-page parallel LLM calls

Tempting for latency: parallelize all 12 pages of a vision-LLM extraction. Rejected because: (a) it amplifies the impact of a circuit-breaker open state (12 simultaneous failures vs. 1), (b) per-page idempotency keys clash with concurrent retries unless very careful, (c) `OCR_VISION_CONCURRENCY` could be added later, but the PRD §3 US-06 explicitly says "in series, not in parallel, to control cost". The series flow honors the PRD.

### Embedding-based deduplication ("variants" of the same contract)

Mentioned in F1 §10 Open Question 6. Rejected at MVP because: (a) embedding compute cost per submission, (b) ambiguity of threshold, (c) the strict-hash deduplication is sufficient for the common case (re-uploads of the exact same file). Documented for future consideration.

---

**End of document.**
