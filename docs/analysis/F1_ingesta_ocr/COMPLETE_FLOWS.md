# Complete Flows — F1: Ingestion & Text Extraction Pipeline

> Generated: 2026-05-15
> Audience: frontend developer, QA engineer, integration engineer
> Source: `PRD_F1_INGESTA_Y_OCR.md` §3, §7 + cross-cutting decisions in `../_shared/GLOBAL_ASSUMPTIONS.md`

---

## Flow Index

| # | Flow Name | Type | Complexity |
|---|---|---|---|
| 1 | Web upload — happy path | Sync request, async processing | Medium |
| 2 | Status polling | Sync request | Low |
| 3 | Web upload — duplicate by hash | Sync request | Low |
| 4 | WhatsApp upload — multi-message session | Async webhook | High |
| 5 | WhatsApp upload — session timeout (no "listo") | Async webhook + cron | Medium |
| 6 | Vision LLM extraction (scanned PDF / image) | Worker | High |
| 7 | Tesseract fallback after vision partial failure | Worker | Medium |
| 8 | Language rejection (not Spanish) | Worker | Low |
| 9 | Submission stuck > 1 hour | Cron | Low |
| 10 | Internal manual retry (operator) | Internal API | Low |

---

## Flow 1: Web upload — happy path

### Actors

| Actor | Role |
|---|---|
| User | Anonymous web user with a contract to analyze |
| Web Frontend | Next.js app that hosts the upload form |
| F1 API | DRF SubmissionViewSet |
| F1 Worker | Asynchronous ingestion worker |

### Pre-conditions

- The user has loaded the upload page and is in El Salvador (no geofence applied; this is preference)
- The user has accepted the on-page disclaimer
- The frontend has obtained the `disclaimer_accepted=true` flag

### Trigger

The user clicks "Analizar mi contrato" after selecting one or more files.

---

### Happy Path

**1. Frontend → Backend (submit)**

- Action: User submits the form
- Request: `POST /v1/contracts/submit`
- Headers: `Content-Type: multipart/form-data; boundary=...`
- Payload (multipart fields):
  - `files` (one or more File parts)
  - `disclaimer_accepted` = `"true"`
  - `delivery_channel` ∈ {`email_pdf`, `whatsapp_summary`, `web_link`}
  - `delivery_target` (string; required for email_pdf and whatsapp_summary, optional for web_link)
  - `force_strategy` (string, optional; `pypdf`/`vision_llm`/`tesseract`; QA only)

**2. Backend — Input Validation**

- Required fields: `files` (≥ 1), `disclaimer_accepted=true`, `delivery_channel`
- Per-file checks:
  - MIME in `application/pdf`, `image/jpeg`, `image/png`, `image/heic`, `image/webp`
  - Size ≤ 15 MB
  - For PDFs: page count ≤ 50 individually
  - For images: dimensions in `[600x800, 8000x10000]`
  - Content > 1 KB
  - For PDFs: no JavaScript or interactive forms (`PDF_NOT_SAFE` if so — F1 OQ-5)
- Submission-level checks:
  - File count in `[1, 50]`
  - Total size ≤ 100 MB
  - Total pages (PDF pages + image count) ≤ 80
- Disclaimer: `disclaimer_accepted == "true"`; if not → E-7
- `delivery_target` format:
  - `email_pdf`: simple email regex
  - `whatsapp_summary`: E.164 (`+503XXXXXXXX`)
  - `web_link`: ignored
- If any validation fails → corresponding 4xx; see Error Scenarios below

**3. Backend — Idempotency check**

- Compute `submission_hash = SHA256(SORT(file1_hex) || "\n" || SORT(file2_hex) || ...)` over file SHA-256 digests sorted by original filename
- Lookup: `SELECT * FROM contract_analysis WHERE submission_hash = $1 AND anonymized_at IS NULL`
- If found and `rubric_version == active_rubric_version`: return 409 (see Flow 3)
- Else: continue

**4. Backend — Business Logic (CQRS Chain)**

- View calls `ingestion_service.accept_web_submission(payload, files)`
- Service generates `public_short_id` (`CS-{YYYY}-{6 base32 chars}`)
- Service hashes the `delivery_target` (salt+SHA-256) → `delivery_target_hash`
- Service calls `analysis_stub_repository.create_stub(...)`:
  - INSERTs into `contract_analysis` with `project_id = '__unknown_pending__'` placeholder, `delivery_channel`, `delivery_target_hash`, `link_expires_at = NOW() + 30 days`, `delivery_status = 'pending'`, `created_at = NOW()`, `submission_hash`
  - Returns `analysis_id`
- Service creates the `ContractSubmission` domain entity with `processing_status = RECEIVED`, `disclaimer_accepted_at = NOW()`, `expires_at = NOW() + 24h`, `analysis_id`
- Service calls `submission_handlers.create_submission(CreateSubmission(submission), submission_repository)` → INSERT into `contract_submission`
- Service publishes `XADD ingestion.submissions {submission_id, files_blob_ref}` to Redis
- Service returns a `SubmissionAcceptedView`

**5. Backend → Frontend (response)**

- HTTP Status: `201 Created`
- Response Body:
```json
{
    "submission_id": "550e8400-e29b-41d4-a716-446655440000",
    "public_short_id": "CS-2026-A1B2C3",
    "analysis_id": "660f8400-...-446655440000",
    "processing_status": "received",
    "estimated_completion_seconds": 90,
    "status_url": "/v1/contracts/550e8400-e29b-41d4-a716-446655440000/status"
}
```

**6. Frontend — Response Handling**

- Save `public_short_id` and `status_url` in local state
- Show a "Tu análisis está listo en menos de 90 segundos. ID: CS-2026-A1B2C3" message
- Begin polling `status_url` every 3 seconds (see Flow 2)

**7. Async — Worker picks up submission**

- The Celery `process_submission` task is dispatched by the view (`process_submission.delay(submission_id)`); the worker process picks it up from the Celery queue
- Reads the in-memory files via the blob ref (Redis blob with TTL ≤ 300 s)
- Calls `IngestionService.start_extraction(submission_id)`:
  - UPDATEs `processing_status = EXTRACTING`, `processing_started_at = NOW()`
  - Hands off to `ExtractionOrchestrator.extract(submission, files)`
- Orchestrator decides strategy, runs it, runs language detection
- Orchestrator returns `ExtractedDocument(text, strategy, tokens, ...)`
- Service:
  - UPDATEs `processing_status = EXTRACTED`, `extraction_strategy_attempted`, `extraction_strategy_successful`, `extracted_text_token_count`, `extracted_text_language`, `extracted_text_language_confidence`, `processing_completed_at = NOW()`
  - Publishes `XADD pipeline.classification {submission_id, analysis_id, extracted_text, extraction_metadata}` to Redis (envelope per `_shared/GLOBAL_ASSUMPTIONS.md` §13)
  - Calls `XACK` on the ingestion stream
- Worker discards in-memory file refs and Redis blobs

---

### Error Scenarios

| ID | Condition | HTTP Status | Response Body (Spanish for user-facing) | Frontend Behavior |
|---|---|---|---|---|
| E-1 | Unsupported format | `400` | `{"error":{"code":"FORMAT_NOT_SUPPORTED","message":"Solo aceptamos PDF, JPG, PNG, HEIC, o WEBP.","details":{"rejected_files":["contract.docx"]}}}` | Inline error |
| E-2 | File too large | `413` | `{"error":{"code":"FILE_TOO_LARGE","message":"El archivo excede 15 MB.","details":{"max_size_mb":15,"actual_size_mb":22.4,"filename":"contract.pdf"}}}` | Inline error |
| E-3 | Total size too large | `413` | `{"error":{"code":"TOTAL_SIZE_TOO_LARGE","message":"La suma de archivos excede 100 MB."}}` | Inline error |
| E-4 | Too many files | `400` | `{"error":{"code":"TOO_MANY_FILES","message":"Máximo 50 archivos por análisis."}}` | Inline error |
| E-5 | Too many pages | `400` | `{"error":{"code":"TOO_MANY_PAGES","message":"Máximo 80 páginas por análisis."}}` | Inline error |
| E-6 | Image dimensions invalid | `400` | `{"error":{"code":"IMAGE_DIMENSIONS_INVALID","message":"Las dimensiones de la imagen están fuera de rango."}}` | Inline error |
| E-7 | Disclaimer not accepted | `400` | `{"error":{"code":"DISCLAIMER_REQUIRED","message":"Acepta el disclaimer para continuar."}}` | Show disclaimer checkbox |
| E-8 | Empty file | `400` | `{"error":{"code":"FILE_EMPTY","message":"El archivo {name} está vacío o corrupto."}}` | Inline error |
| E-9 | PDF unsafe (JS/forms) | `400` | `{"error":{"code":"PDF_NOT_SAFE","message":"Este PDF contiene scripts o formularios interactivos. Exporta una versión sin estos elementos."}}` | Inline error |
| E-10 | Invalid `delivery_channel` | `400` | `{"error":{"code":"INVALID_DELIVERY_CHANNEL"}}` | Reset channel selector |
| E-11 | Invalid `delivery_target` for channel | `400` | `{"error":{"code":"INVALID_DELIVERY_TARGET","message":"El correo o teléfono no es válido."}}` | Inline error |
| E-12 | Rate limit (5/h/IP) | `429` | `{"error":{"code":"RATE_LIMITED","message":"Has excedido el límite. Intenta en una hora."}}` + `Retry-After` header | Show backoff message |
| E-13 | Server error during stub creation | `500` | `{"error":{"code":"INTERNAL_ERROR","correlation_id":"..."}}` | "Algo falló, intenta de nuevo" |
| E-14 | Duplicate (same hash, same rubric) | `409` | See Flow 3 | Auto-redirect to existing analysis |

---

### Post-conditions

**On success (201):**

- `contract_submission` row exists with `processing_status=received` and `analysis_id` populated
- `contract_analysis` stub row exists with `delivery_status=pending`, `project_id=__unknown_pending__`
- `XADD ingestion.submissions` published; the worker will process it within seconds
- The user has `public_short_id` and a status URL

**On failure (4xx/5xx):**

- No persistent rows are created
- Any in-memory blobs are released
- No charges to OpenRouter or any external service

---

### Async / Background Behavior

- **Worker**: Celery `process_submission` task (default worker concurrency 4 via `CELERY_WORKER_CONCURRENCY`)
- **Triggered by**: `XADD ingestion.submissions` from this flow
- **Retry policy**: at-least-once delivery; idempotency via `submission_id` + `processing_status` guard (worker checks the status is `received` before processing)
- **Timeout**: 5 minutes per submission (`BR-07`)
- **Side effect**: when extraction completes, `XADD pipeline.classification` fires for F2

---

## Flow 2: Status polling

### Actors

| Actor | Role |
|---|---|
| Anonymous user (via frontend or direct API call) | Asks for processing state |

### Pre-conditions

- A `ContractSubmission` row exists for the given `submission_id` or `public_short_id`
- The row has not expired (`expires_at > NOW()`)

### Trigger

Frontend `setInterval(poll, 3000)` until terminal state.

---

### Happy Path

**1. Frontend → Backend**

- Action: poll
- Request: `GET /v1/contracts/{submission_id_or_short_id}/status`
- Headers: none required

**2. Backend — Lookup**

- Try to parse `{id}` as UUID first → query `contract_submission.id`
- If not UUID-shaped → query `contract_submission.public_short_id`
- If found → return the view
- If not found → `404`

**3. Backend — Response**

- For `processing_status in ['received','extracting']`:
```json
{
    "submission_id": "...",
    "public_short_id": "CS-2026-A1B2C3",
    "processing_status": "extracting",
    "progress": {
        "stage": "OCR",
        "pages_processed": 5,
        "pages_total": 12,
        "estimated_remaining_seconds": 35
    },
    "started_at": "2026-05-10T14:23:01Z",
    "analysis_id": null,
    "error": null
}
```

- For `processing_status='completed'`:
```json
{
    "submission_id": "...",
    "public_short_id": "CS-2026-A1B2C3",
    "processing_status": "completed",
    "analysis_id": "...",
    "report_url": "/v1/reports/CS-2026-A1B2C3",
    "started_at": "...",
    "completed_at": "..."
}
```

- For `processing_status in ['rejected_language','failed_extraction',...]`:
```json
{
    "submission_id": "...",
    "processing_status": "rejected_language",
    "error": {
        "code": "LANGUAGE_NOT_SUPPORTED",
        "message": "Detectamos que el contrato está en inglés. Casa Segura solo analiza contratos en español por ahora.",
        "user_facing": true
    }
}
```

- HTTP Status: `200`
- Cache headers: `Cache-Control: no-cache`

**4. Frontend — Response Handling**

- If `processing_status` ∈ terminal set (`completed`, `rejected_*`, `failed_*`, `expired`): stop polling, show appropriate UI
- Else: continue polling

---

### Error Scenarios

| ID | Condition | HTTP Status | Response Body | Frontend Behavior |
|---|---|---|---|---|
| E-1 | ID not found / expired | `404` | `{"error":{"code":"SUBMISSION_NOT_FOUND"}}` | "Tu análisis ya expiró. Sube de nuevo." |
| E-2 | Malformed ID | `400` | `{"error":{"code":"INVALID_ID_FORMAT"}}` | "ID inválido" |

---

### Post-conditions

- No state changes; this is a read-only flow.

---

## Flow 3: Web upload — duplicate by hash

### Trigger

A `POST /v1/contracts/submit` whose `submission_hash` matches an existing non-anonymized `ContractAnalysis` and the rubric version matches.

### Happy Path

**1. Backend — Detect**

- After step 3 of Flow 1, the lookup finds a matching analysis
- Active rubric version (`rubric_version` table where `is_active=true`) matches the prior analysis's `rubric_version`

**2. Backend — Response**

- HTTP Status: `409 Conflict`
- Response Body:
```json
{
    "submission_id": "{previous_submission_id}",
    "public_short_id": "CS-2026-PREV01",
    "processing_status": "completed",
    "analysis_id": "{previous_analysis_id}",
    "is_duplicate": true,
    "message": "Este contrato ya fue analizado previamente. Te entregamos el análisis existente."
}
```

**3. Frontend — Behavior**

- Auto-navigate to `/r/{public_short_id}` so the user sees their existing report
- Do NOT re-trigger the delivery flow (the user already received the report on the first submission)

### Alternate path — different rubric version

- The lookup finds the analysis but the active rubric is newer
- Backend creates a new `ContractSubmission` + new stub `ContractAnalysis` (sharing `submission_hash` and `project_id`)
- Returns 201 as in Flow 1

---

## Flow 4: WhatsApp upload — multi-message session

### Actors

| Actor | Role |
|---|---|
| User (WhatsApp) | Sends photos one-by-one |
| Zavu | Carries messages, signs webhooks |
| F1 webhook | Receives messages |
| F1 Worker | Processes the submission once the session closes |

### Pre-conditions

- Zavu is configured with a webhook pointing to `POST /v1/zavu/webhook`
- The user has the WhatsApp Business number saved or has clicked a WhatsApp deep link

### Trigger

The first message from a `from_number` that has no active session.

---

### Happy Path

**1. Zavu → Webhook (welcome)**

- Action: First file arrives
- Request: `POST /v1/zavu/webhook`
- Headers: `X-Zavu-Signature: sha256=<hmac>`
- Body:
```json
{
    "message_id": "zavu-msg-001",
    "from_number": "+50312345678",
    "received_at": "2026-05-10T14:23:01Z",
    "type": "media",
    "media": [{"url":"https://signed.zavu/...","mime_type":"image/jpeg","size_bytes":2400000}],
    "text": null
}
```

**2. Backend — Verify signature**

- Compute `hmac_sha256(secret, raw_body)`, compare against `X-Zavu-Signature`
- If mismatch → 401 + log attempt + do NOT process

**3. Backend — Hash phone**

- `phone_hash = sha256(salt + from_number)`
- (Salt is the global system salt, env var `PHONE_HASH_SALT`)

**4. Backend — Session lookup**

- `GET whatsapp_session:{phone_hash}` from Redis
- Not found → start new session
- `SETEX whatsapp_session:{phone_hash} 300 {disclaimer_accepted:false, files:[{...}], started_at:ts}`

**5. Backend → Zavu (welcome message)**

- POST to Zavu API with template `casa_segura_welcome` (already approved):
```
¡Hola! Soy Casa Segura. Te ayudo a revisar tu contrato inmobiliario antes de firmarlo.

⚠️ Importante: lo que te diga NO es asesoría legal. Es orientación basada en leyes salvadoreñas. Antes de firmar, consulta a un abogado.

Si aceptas y quieres continuar, responde "acepto". Después mándame las fotos o el PDF de tu contrato.
```

**6. Zavu → User**

- Message arrives in WhatsApp

**7. User → Zavu → Webhook (acepto)**

- Text "acepto" (or variants: "si", "sí", "ok", "de acuerdo")
- Webhook processes: `mark_disclaimer_accepted(phone_hash)`

**8. User sends more files**

- For each: append to session's `files` list; `EXPIRE 300`

**9. User → Zavu → Webhook (listo)**

- Text "listo" (or `finalizar`, `enviar`, `procesar`, `terminé`, case-insensitive, accent-insensitive)
- Backend closes the session

**10. Backend — Close session**

- Read final payload from Redis
- DEL session key
- If disclaimer not accepted: send "No recibí tu acepto. Empieza de nuevo." → no submission
- If disclaimer accepted:
  - Download each file via signed URL → in-memory bytes
  - Compute submission hash
  - Dedupe (Flow 3 applies)
  - Create stub `ContractAnalysis` with `delivery_channel='whatsapp_summary'`, `delivery_target=phone`, `delivery_target_hash=sha256(salt+phone)`
  - Create `ContractSubmission` (`source='whatsapp'`, `source_metadata={phone_hash, zavu_msg_ids:[...]}`)
  - `XADD ingestion.submissions`

**11. Backend → Zavu**

- Send confirmation: "Gracias. Estoy analizando tu contrato. Te mando el resultado en menos de 2 minutos."

---

### Error Scenarios

| ID | Condition | Response | User-facing behavior |
|---|---|---|---|
| E-1 | Invalid signature | 401 | None to user (silent drop + log) |
| E-2 | Unsupported file format mid-session | Webhook responds 200 to Zavu | WhatsApp reply: "Mandaste un archivo en formato no soportado. Solo acepto PDF, JPG, PNG, HEIC, WEBP. La sesión sigue abierta." |
| E-3 | Session has > 50 files | Webhook responds 200 | WhatsApp reply: "Recibí muchos archivos. Cerrando sesión, procesando los 50 primeros." (force-close) |
| E-4 | User sends `cancelar` / `borrar` | Webhook responds 200 | DEL session key; reply: "Cancelé tu envío. Si quieres analizar tu contrato, mándamelo de nuevo." |
| E-5 | User sends text without files first | Webhook responds 200 | Reply with instructions |
| E-6 | Same `from_number` submits 4th time in an hour | Webhook responds 200 | Reply: "Has excedido el límite. Intenta más tarde." |

### Post-conditions

- On success: same as Flow 1 (one `contract_submission` + one stub `contract_analysis`)
- On cancel/timeout: Redis key deleted; no DB writes

---

## Flow 5: WhatsApp upload — session timeout

### Trigger

`whatsapp_session:{phone_hash}` Redis key expires after 300 seconds without user activity.

### Happy Path

**1. Redis emits keyspace notification**

- Requires `notify-keyspace-events Ex` in Redis config
- `SessionExpiryListener` (subscribed to `__keyevent@0__:expired`) receives the event

**2. Listener — Read final state**

- A separate Redis HSET `whatsapp_session_final:{phone_hash}` was kept with the session payload (set with a slightly longer TTL of 600 s so the listener can read it AFTER expiration of the main key)
- Listener reads `whatsapp_session_final:{phone_hash}`
- If found and disclaimer was accepted AND files ≥ 1:
  - Same as Flow 4 step 10 (create submission)
  - Send WhatsApp message: "Cerré tu sesión por inactividad. Estoy procesando los archivos que me mandaste."
- If disclaimer not accepted OR no files:
  - DEL `whatsapp_session_final:{phone_hash}`
  - Send WhatsApp message: "No procesé tu envío (no recibí tu acepto o no recibí archivos). Empieza de nuevo si quieres."

---

## Flow 6: Vision LLM extraction

### Trigger

Worker picks up `XADD ingestion.submissions` for a submission whose strategy diagnosis returned `VISION_LLM` (either because the file is an image or because `pypdf` could not extract text from page 1).

### Happy Path

**1. Worker → Orchestrator → VisionLlmExtractor**

- `Orchestrator.extract(submission, files_in_memory)`
- For each file: if PDF → rasterize at 150 DPI via `pdf2image.convert_from_bytes(...)`; if image → convert HEIC/WEBP to JPEG, clamp longest dim to 1920 px
- Create `OcrJob(strategy=VISION_LLM, attempt_number=1, model_used=anthropic/claude-sonnet-4)` → returns `job_id`

**2. Per-page loop**

For each page index `n` of `total`:
- Build prompt from `PRD_F1` §8.1 (system) + `§8.2` (user with page number)
- Build idempotency key: `submission_id:p{n}:vision_llm:1`
- Call `OpenRouterClient.chat_completion_vision(model, image, prompt, idempotency_key)`
  - Timeout: 60 s per page
  - On transient error (timeout, 429, 5xx): retry with backoff 1 s, then 4 s; max 2 retries; same idempotency key
  - On permanent error (400, 401, 422 with invalid content): mark page failed and continue
- Append text with separator `\n\n--- PAGE N ---\n\n`
- Strip meta-comments (regex: `^(Aquí está|Here is|I have transcribed).*?:\s*` and similar)
- If meta-comment > 5% of output: retry with reinforced prompt from `PRD_F1` §8.2

**3. Per-page outcome**

- If `failed_pages / total_pages ≤ 0.30`: continue to language detection
- If `failed_pages / total_pages > 0.30`: escalate to Tesseract fallback (Flow 7) if `OCR_TESSERACT_ENABLED=true`; else mark submission `failed_extraction`

**4. Complete job**

- UPDATE `ocr_job SET status='success'|'failed', completed_at=NOW(), pages_processed, pages_failed, tokens_consumed=sum, cost_estimate_cents=sum`

**5. Language detection** (see Flow 8)

**6. Return to Worker**

- `ExtractedDocument(text, strategy=VISION_LLM, pages_processed, pages_failed, tokens_consumed, cost_estimate_cents)`

### Error Scenarios

| ID | Condition | Outcome |
|---|---|---|
| E-1 | Total per-submission timeout (> 5 min) | Mark submission `failed_extraction`, `error_code=TIMEOUT_EXCEEDED` |
| E-2 | Circuit breaker open (5 consecutive failures in 60 s) | Use Tesseract directly for new submissions; existing submissions in flight may complete partially |
| E-3 | OpenRouter 401 (bad key) | Mark submission `failed_extraction`, `error_code=LLM_AUTH_FAILED`; fire ops alert |
| E-4 | HEIC decode failure | Mark file as failed; the remaining files in the submission may still proceed |
| E-5 | Image dimension exceeded post-clamp | Should not happen; if it does, treat as permanent error for that page |

### Post-conditions

- `OcrJob` row with cost and status persisted
- `extracted_text` passed in-memory to the next stage; never persisted
- `ContractSubmission` row updated

---

## Flow 7: Tesseract fallback after vision partial failure

### Trigger

Vision LLM extraction reported `pages_failed / total > 0.30` AND `OCR_TESSERACT_ENABLED=true`.

### Happy Path

**1. Orchestrator → TesseractExtractor**

- For each failed page (or all pages if vision LLM produced 0 valid pages):
  - For PDFs: rasterize the page at the configured DPI
  - For images: apply preprocessing (grayscale → contrast adjust → Otsu binarization) using Pillow
  - Call `pytesseract.image_to_data(image, lang='spa', output_type='dict')`
  - Compute average confidence (mean of token confidences > 0)
  - If avg confidence < 60: mark page failed
  - Else: append `text` joined by spaces, preserved line breaks where Tesseract reports them

**2. Outcome**

- If every failed page succeeded → merge with vision-LLM text (interleave by page number) → pass to language detection
- If any page still failed → mark submission `failed_extraction`, `error_code=EXTRACTION_FAILED`

### Error Scenarios

| ID | Condition | Outcome |
|---|---|---|
| E-1 | `tesseract` binary missing | Worker boot fails; ops alert |
| E-2 | Spanish language pack `spa.traineddata` missing | Mark submission `failed_extraction`, `error_code=TESSERACT_LANG_MISSING` |
| E-3 | Per-page timeout (30 s) | Mark page failed; if quota exceeded, submission fails |

---

## Flow 8: Language rejection

### Trigger

After successful extraction, `LanguageDetector.detect(first_2000_chars)` returns either: (a) confidence < 0.85, or (b) confidence ≥ 0.85 with a language code other than `es`.

### Happy Path

**1. Orchestrator decides**

- If `(lang, confidence)` is `("es", c >= 0.85)`: continue (NOT this flow)
- If `(lang, confidence)` is `("es", c < 0.85)`: continue with logged warning (technical/legal Spanish with proper nouns can fall here)
- If `(lang, confidence)` is `(not "es", c >= 0.85)`: → REJECT
- If `(lang, confidence)` is `(not "es", c < 0.85)`: → REJECT

**2. Worker updates**

- UPDATE `contract_submission SET processing_status='rejected_language', error_code='LANGUAGE_NOT_SUPPORTED', error_reason='Detected language: <lang> (confidence <c>)', processing_completed_at=NOW()`
- Discard extracted text and file blobs

**3. No publication**

- Do NOT `XADD pipeline.classification`
- The status endpoint will return `rejected_language` on the user's next poll

**4. User-facing message**

- Web: status endpoint returns `error.message = "Detectamos que tu contrato no está en español. Casa Segura solo analiza contratos en español por ahora."`
- WhatsApp: F7 sends a message with the same content (the welcome path also handles this case)

### Post-conditions

- No charge to F2 (because no F2 invocation happens)
- The submission expires in 24 hours

---

## Flow 9: Submission stuck > 1 hour

### Trigger

Cron job runs hourly; finds submissions where `processing_status IN ('received','extracting','classifying')` AND `processing_started_at < NOW() - INTERVAL '1 hour'`.

### Happy Path

**1. Cron — Identify**

- Query: `SELECT id FROM contract_submission WHERE processing_status IN (...) AND processing_started_at < NOW() - INTERVAL '1 hour'`

**2. Cron — Mark**

- `UPDATE contract_submission SET processing_status='expired', error_code='STUCK_IN_PROCESSING', error_reason='Submission stuck in processing', processing_completed_at=NOW() WHERE id IN (...)`

**3. Cleanup**

- Any in-memory work for that submission is orphaned (the worker should detect the status change on its next progress UPDATE and abort)

### Post-conditions

- The user's next poll of status returns `expired`
- The row is hard-deleted after `expires_at` (24 h)

---

## Flow 10: Internal manual retry (operator)

### Trigger

An operator decides a stuck or failed submission deserves another try (e.g., OpenRouter outage was the cause, now resolved).

### Happy Path

**1. Operator → Internal API**

- Request: `POST /v1/internal/submissions/{submission_id}/retry-ocr`
- Headers: `X-Internal-Auth: <secret>`
- Body (optional):
```json
{ "force_strategy": "tesseract" }
```

**2. Backend — Reset**

- Verify `X-Internal-Auth`
- Verify the submission's `expires_at > NOW()` (not yet expired)
- UPDATE `processing_status='received'`, `extraction_strategy_attempted=null`, `error_code=null`
- (No new `OcrJob` rows; the next retry attempt creates them)
- Re-publish `XADD ingestion.submissions {submission_id, file_refs_in_memory_or_null}`
- If file refs are no longer in memory (likely; 5-min Redis TTL expired): respond 422 `EXTRACTION_FILES_GONE` because F1 doesn't retain raw bytes after the first attempt

**3. Backend — Response**

- `202 Accepted` if requeued
- `422 Unprocessable Entity` if files are gone

### Notes

This is a debug/QA flow, not a user-facing flow. PRD_F1 OQ-2 lists this as an open question; the proposed default is internal-only, no public endpoint, to avoid OpenRouter cost abuse.

---

**End of document.**
