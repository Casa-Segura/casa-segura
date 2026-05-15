# Complete Flows — F2: Contract Classification & Structured Extraction

> Generated: 2026-05-15
> Source: `PRD_F2_CLASIFICACION.md` §3, §7 + cross-cutting decisions

---

## Flow Index

| # | Flow Name | Type | Complexity |
|---|---|---|---|
| 1 | Standard classification (high confidence) | Worker | Medium |
| 2 | Medium confidence → validation retry | Worker | Medium |
| 3 | Reclassification CVP→LEA | Worker | High |
| 4 | NOT_CLASSIFIABLE rejection | Worker | Low |
| 5 | Economic field extraction | Worker | Medium |
| 6 | Project name fallback to placeholder | Worker | Low |
| 7 | LLM failure → failed_classification | Worker | Medium |
| 8 | Internal classify endpoint (QA) | Sync request | Low |

---

## Flow 1: Standard classification (high confidence)

### Actors

| Actor | Role |
|---|---|
| F1 | Publishes `ExtractionDone` to Redis stream |
| ClassificationConsumer | Daemon that dispatches Celery tasks |
| ProcessClassificationTask | Celery worker task |
| ClassificationService | Orchestration class |

### Pre-conditions

- `ContractAnalysis` stub exists with `project_id = '__unknown_pending__'`, `submission_hash`, `public_short_id`, `delivery_*` set by F1
- The active rubric/corpus/benchmark versions are set in `platform`'s version catalogs

### Trigger

Redis stream `ingestion.to_classification` receives a new entry.

---

### Happy Path

**1. Consumer → Task**

- Daemon calls `XREADGROUP > classification GROUP classification:c1`
- Parses the message into `ExtractionDone`
- Calls `process_classification.delay(envelope_json=...)`
- `XACK`

**2. Task — Classification call**

- Service starts a `ClassificationJob` (step=classification, attempt=1, status=running)
- POST `https://openrouter.ai/api/v1/chat/completions` with:
  - model: `anthropic/claude-sonnet-4`
  - messages: system from PRD §8.1, user from PRD §8.2 (interpolating `extracted_text`)
  - `response_format`: `{"type": "json_object"}`
  - `temperature`: 0.1
  - `Idempotency-Key`: `{submission_id}:f2:classification`
- Receives JSON with `contract_type`, `confidence`, `indicators_found`, `reasoning`, `project_name_canonical`, `elements_detected`
- Completes job: status=success, tokens, cost
- `confidence ≥ 0.85` → accept

**3. Task — Economic call (if applicable)**

- `contract_type in {CVP, APV, LEA, FSV, ARV}` → run economic step
- Same shape; output validated against `EconomicFieldsRaw`

**4. Task — Project lookup**

- Normalize project name (lowercase, strip accents, drop generic words, collapse spaces)
- Postgres upsert by `normalized_name`
- Receive `project_id`

**5. Task — Persist**

- UPDATE `contract_analysis` set:
  - `contract_type`, `contract_type_declared` (= classified type)
  - `contract_type_reclassified=false`, `reclassification_reason=NULL`
  - `classification_confidence`, `classification_attempts=1`
  - `elements_detected` (JSONB)
  - `project_id` (replaces placeholder)
  - `rubric_version` (= active rubric)

**6. Task — Publish to F4/F5**

- `XADD classification.to_rubric_and_economics * envelope=...`

---

### Error Scenarios

| ID | Condition | Outcome |
|---|---|---|
| E-1 | LLM 401 (bad key) | `ClassificationJob.status=failed`, `error_code=LLM_AUTH_FAILED`; submission → `failed_classification`; ops alert |
| E-2 | LLM transient 5xx | Retry once (`max_retries=1`); if second attempt fails → `failed_classification` |
| E-3 | LLM returns non-JSON / malformed | Try parser recovery (strip fences, balanced-brace extraction); if still fails → retry once → `failed_classification` |
| E-4 | LLM returns `contract_type` outside enum | Treat as `NOT_CLASSIFIABLE` |
| E-5 | LLM exceeds 30 s timeout | Cancel; retry once; if again → `failed_classification` |
| E-6 | Postgres unavailable | Celery autoretry with backoff; submission stays `extracted` |
| E-7 | Circuit breaker open | Fast-fail; submission → `failed_classification` with `error_code=LLM_CIRCUIT_OPEN` |

### Post-conditions

- `contract_analysis` row complete (F2-owned columns filled)
- F4 and F5 see the message and start their work independently
- `ContractSubmission.processing_status` transitions to `classifying` (during) and remains `classifying` until F4 publishes — F4 will set `analyzing` later

---

## Flow 2: Medium confidence → validation retry

### Trigger

Step 2 of Flow 1 returns `confidence ∈ [0.65, 0.85)`.

### Happy Path

1. Service emits a second `ClassificationJob` (step=classification, attempt=2)
2. POST OpenRouter with PRD §8.3 prompt and idempotency key `{submission_id}:f2:classification_validation`
3. Parse `contract_type`, `confidence`
4. Compare:
   - If types agree → accept; `classification_attempts=2`; proceed to step 3 of Flow 1
   - If types disagree → mark NOT_CLASSIFIABLE (Flow 4)

### Notes

- The validation prompt is reinforced and instructs the model to be extra rigorous
- The two responses are logged separately with the `attempt_number` field for post-hoc analysis

---

## Flow 3: Reclassification CVP→LEA

### Trigger

Step 2 of Flow 1 accepts `contract_type ∈ {CVC, CVP, APV}`.

### Happy Path

1. Service emits `ClassificationJob(step=leasing_detection)`
2. POST OpenRouter with PRD §8.4 prompt and idempotency key `{submission_id}:f2:leasing`
3. Parse `LeasingIndicators`:
   - `indicators_count = sum(detected for indicator in 6)`
   - `should_reclassify = indicators_count >= 4` (configurable threshold)
4. If reclassify:
   - `result.contract_type = LEA`
   - `result.contract_type_declared = original type`
   - `result.contract_type_reclassified = true`
   - `result.reclassification_reason` = textual list, e.g. "5 of 6 Art. 2 LAF indicators present: mandatory_term, predefined_purchase_option, ownership_retained, taxes_to_buyer, risks_to_buyer."
   - `result.reclassification_indicators` = the full `LeasingIndicators` Pydantic object (JSON-serialized into `contract_analysis.reclassification_indicators` column)
5. If 2–3 indicators: no reclassification, but `reclassification_indicators` is still persisted as a yellow-finding hint for F4
6. If 0–1: discard the indicators (none persisted)

### Notes

- The threshold default is 4 of 6 (PRD §3 US-03, PRD §10 OQ-1 open). Configurable via env var `LEASING_RECLASSIFICATION_THRESHOLD`.
- This step does **not** consult F3; the legal anchor (Art. 2 LAF) is the criterion's responsibility in F4.

---

## Flow 4: NOT_CLASSIFIABLE rejection

### Trigger

- Confidence < 0.65 after first or second attempt
- LLM returns `contract_type = "NOT_CLASSIFIABLE"` directly
- Two attempts disagree

### Happy Path

1. Service marks the result `contract_type = NOT_CLASSIFIABLE`
2. UPDATE `contract_analysis`:
   - `contract_type = "NOT_CLASSIFIABLE"`
   - `classification_confidence` = whatever was returned
   - `classification_attempts` = 1 or 2
3. UPDATE `contract_submission`:
   - `processing_status = "rejected_type"`
   - `error_code = "TYPE_NOT_SUPPORTED"`
   - `error_reason = "Detected contract type is not covered by Casa Segura."`
   - `processing_completed_at = NOW()`
4. Do **not** publish to F4/F5 streams
5. Notify the user:
   - Web: status endpoint returns `error.message` translated to Spanish
   - WhatsApp: send template message `not_classifiable_explanation` via Zavu

### Post-conditions

- Pipeline halts at F2
- No charge to F3, F4, F5
- Project assignment is not performed (no project_id update beyond the placeholder)
- The user receives a clear message in Spanish; can resubmit

---

## Flow 5: Economic field extraction

### Trigger

Classification accepted (possibly after reclassification), and `contract_type ∈ {CVP, APV, LEA, FSV, ARV}`.

### Happy Path

1. Service emits `ClassificationJob(step=economic_extraction)`
2. POST OpenRouter with PRD §8.5 prompt
3. Parse `EconomicFieldsRaw`:
   - Each field has `value`, `confidence`, `evidence_snippet` (snippet ≤ 500 chars, used by F4 as `evidence_clause_snippet` for the finding)
   - If `monthly_rate_pct` is present but `annual_rate_pct` is not: compute derived annual via compound formula; record `extraction_note = "converted from monthly rate"`
   - Validate ranges (e.g., `annual_rate_pct` must be in [0, 1]) — if out of range, set `extraction_status=invalid` and skip
   - If `interest_calculation_base == "total_balance"`: flag for F4 as potential `art_12_lpc` override candidate
4. Pass `EconomicFieldsRaw` as part of `ClassificationDone.economic_fields_raw` to F4 and F5

### Notes

- F2 does **not** persist these fields directly — they live in memory until F5 normalizes and writes `economic_summary`
- F5 is the validator; F2's job is extraction

---

## Flow 6: Project name fallback to placeholder

### Trigger

Step 2 of Flow 1 returns `project_name_canonical = null` or the normalized name is shorter than 3 characters.

### Happy Path

1. `short_hash = submission_hash[:8]`
2. INSERT `project (canonical_name='Pending project assignment', normalized_name=f'unknown_{short_hash}', first_seen=NOW(), last_analyzed=NOW(), metadata={"placeholder": true})`
3. Use the new `project_id` for `contract_analysis.project_id`

### Notes

- Placeholder projects are **not** reused across submissions (each placeholder is unique by `submission_hash[:8]`)
- They do not contribute to global statistics; F8's recompute job skips rows with `metadata.placeholder=true`
- The user-facing report will say: "El nombre del proyecto no se pudo extraer del contrato. Asociamos este análisis a un placeholder único."

---

## Flow 7: LLM failure → failed_classification

### Trigger

Any LLM call exhausts retries or hits the circuit breaker.

### Happy Path

1. Service catches the failure
2. UPDATE `contract_analysis`:
   - `contract_type = NULL` (still empty)
   - `classification_attempts = N`
3. UPDATE `contract_submission`:
   - `processing_status = "failed_classification"`
   - `error_code` = `LLM_AUTH_FAILED` / `LLM_CIRCUIT_OPEN` / `LLM_TRANSIENT_FAILURE` / `LLM_PARSE_FAILED`
   - `error_reason` = operator-facing description
4. Ops alert (Prometheus counter `f2_failed_classification_total{error_code=...}` → alertmanager)
5. The user is told (web status / WhatsApp message) that the analysis could not be completed; they should retry

### Notes

- `failed_classification` is distinct from `NOT_CLASSIFIABLE`: the former is a system error (transient infra problem), the latter is a product-level rejection
- Manual operator retry via `POST /v1/internal/submissions/{id}/retry-classification` (HasInternalAuthHeader) re-runs F2 only

---

## Flow 8: Internal classify endpoint (QA)

### Trigger

QA engineer wants to test the classifier without F1.

### Happy Path

1. POST `/v1/internal/classify` with `X-Internal-Auth: <secret>`
2. Body: `{ "text": "...", "force_type": null, "skip_leasing_check": false }`
3. The view calls `ClassificationService.classify_text_only(...)` — a path that does **not** persist anything and does **not** publish to F4/F5
4. Returns the full `ClassificationResult` JSON for inspection

### Notes

- The endpoint is rate-limited per IP
- Output includes tokens_consumed and cost_estimate_cents for cost calibration
- This path counts against OpenRouter cost like any other call

---

**End of document.**
