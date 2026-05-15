# Evaluation Coverage — F1: Ingestion & Text Extraction Pipeline

> Generated: 2026-05-15
> Source: `PRD_F1_INGESTA_Y_OCR.md` plus cross-cutting decisions in `../_shared/GLOBAL_ASSUMPTIONS.md`.
> Stack: Django 5.2 LTS + DRF + Celery + Redis + Postgres 15 + pgvector.

---

## PRD Contradictions

No contradictions internal to PRD_F1 were detected after the Step 1 re-read.

Cross-PRD contradictions that touch F1 are documented in `../_shared/GLOBAL_ASSUMPTIONS.md` §3 (`delivery_status`) and §6 (idempotency vs rubric version). Both are MODERATE and have a canonical resolution; the F1 plan honors them.

---

## Coverage Matrix

| PRD Requirement | Covered By | Status |
|---|---|---|
| US-01: web upload with disclaimer + validations | `FEATURE_OVERVIEW.md`, `SOLUTION_DIAGRAMS.md` §2.1, `INTERACTION_DIAGRAMS.md` Flow US-01, `COMPLETE_FLOWS.md` Flow 1, `IMPLEMENTATION_PLAN.md` Story US-01 | COVERED |
| US-02: WhatsApp upload with 5-min session | `SOLUTION_DIAGRAMS.md` §2.3, `INTERACTION_DIAGRAMS.md` Flow US-02, `COMPLETE_FLOWS.md` Flow 4, `IMPLEMENTATION_PLAN.md` Story US-02 | COVERED |
| US-03: hash deduplication, rubric-version aware | `INTERACTION_DIAGRAMS.md` Flow US-03, `COMPLETE_FLOWS.md` Flow 3, `IMPLEMENTATION_PLAN.md` Story US-03 | COVERED |
| US-04: strategy diagnosis (pypdf / vision_llm / tesseract) | `SOLUTION_DIAGRAMS.md` §4 activity, `DESIGN_PATTERNS.md` Strategy, `IMPLEMENTATION_PLAN.md` Story US-04 | COVERED |
| US-05: pypdf extraction | `IMPLEMENTATION_PLAN.md` Story US-05 | COVERED |
| US-06: vision LLM extraction | `SOLUTION_DIAGRAMS.md` §2.2, `INTERACTION_DIAGRAMS.md` Flow US-06, `COMPLETE_FLOWS.md` Flow 6, `IMPLEMENTATION_PLAN.md` Story US-06 | COVERED |
| US-07: Tesseract fallback | `INTERACTION_DIAGRAMS.md` partial-failure sequence, `COMPLETE_FLOWS.md` Flow 7, `IMPLEMENTATION_PLAN.md` Story US-07 | COVERED |
| US-08: Spanish language detection | `SOLUTION_DIAGRAMS.md` §2.5, `COMPLETE_FLOWS.md` Flow 8, `IMPLEMENTATION_PLAN.md` Story US-08 | COVERED |
| US-09: public status endpoint | `COMPLETE_FLOWS.md` Flow 2, `IMPLEMENTATION_PLAN.md` Story US-09 | COVERED |
| US-10: discard original files after processing | `DESIGN_PATTERNS.md` (Pipes & Filters note on TTL), `COMPLETE_FLOWS.md` Flow 1 step 7, `IMPLEMENTATION_PLAN.md` Story US-10 | COVERED |
| BR-01: no file persisted to disk | `IMPLEMENTATION_PLAN.md` Story US-10 acceptance + smoke tests | COVERED |
| BR-02: extracted text not persisted | `IMPLEMENTATION_PLAN.md` Story US-01 (token count only); enforced by absence of any text column | COVERED |
| BR-03: hash deduplication strict, rubric-version aware | `IMPLEMENTATION_PLAN.md` Story US-03 + `_shared/GLOBAL_ASSUMPTIONS.md` §6 | COVERED |
| BR-04: cost-ordered strategy escalation | `SOLUTION_DIAGRAMS.md` §4, `DESIGN_PATTERNS.md` Strategy | COVERED |
| BR-05: LLM idempotency keys | `DESIGN_PATTERNS.md` Idempotency, `IMPLEMENTATION_PLAN.md` Story US-06, `OpenRouterClient` design | COVERED |
| BR-06: per-job cost recorded | `ENTITY_RELATIONSHIP_DIAGRAM.md` `OcrJob.cost_estimate_cents`, `IMPLEMENTATION_PLAN.md` Story US-06 | COVERED |
| BR-07: 5-min total timeout | `IMPLEMENTATION_PLAN.md` config var, `COMPLETE_FLOWS.md` Flow 6 error E-1 | COVERED |
| BR-08: re-escalation when < 500 chars | `IMPLEMENTATION_PLAN.md` Story US-05/US-06, `OCR_MIN_EXTRACTED_TEXT_CHARS` env var | COVERED |
| BR-09: language confidence ≥ 0.85 | `IMPLEMENTATION_PLAN.md` Story US-08, env var `OCR_LANGUAGE_CONFIDENCE_THRESHOLD` | COVERED |
| BR-10: ≤ 50 files | `IMPLEMENTATION_PLAN.md` validators, env var `F1_MAX_FILES` | COVERED |
| BR-11: ≤ 80 total pages | `IMPLEMENTATION_PLAN.md` validators, env var `F1_MAX_PAGES` | COVERED |
| BR-12: WhatsApp session TTL 300 s | `IMPLEMENTATION_PLAN.md` Story US-02, env var `WHATSAPP_SESSION_TTL_SECONDS` | COVERED |
| BR-13: disclaimer required | `IMPLEMENTATION_PLAN.md` Story US-01 validator, error `DISCLAIMER_REQUIRED` | COVERED |
| BR-14: 15-min cleanup cron | Owned by F8; F1 documents the periodic task `mark_stuck_submissions` (hourly) and references F8's `cleanup_transient` (15-min) | COVERED |
| Data model `ContractSubmission` | `ENTITY_RELATIONSHIP_DIAGRAM.md`, `IMPLEMENTATION_PLAN.md` Stage 5 | COVERED |
| Data model `OcrJob` | `ENTITY_RELATIONSHIP_DIAGRAM.md`, `IMPLEMENTATION_PLAN.md` Stage 5 | COVERED |
| Cost view `v_ocr_daily_costs` | `IMPLEMENTATION_PLAN.md` Stage 14 — Prometheus metrics aggregate; the SQL view stays declared in F8 | COVERED |
| API `POST /v1/contracts/submit` | `IMPLEMENTATION_PLAN.md` Story US-01 endpoint table | COVERED |
| API `GET /v1/contracts/{id}/status` | `IMPLEMENTATION_PLAN.md` Story US-09 | COVERED |
| API `POST /v1/zavu/webhook` | `IMPLEMENTATION_PLAN.md` Story US-02 endpoint table | COVERED |
| Error codes (full table) | `IMPLEMENTATION_PLAN.md` "Error Codes" section + `COMPLETE_FLOWS.md` per-flow E-N tables | COVERED |
| Prompts §8.1 / §8.2 / §8.3 | `IMPLEMENTATION_PLAN.md` Story US-06 references; prompts kept verbatim in `vision_llm_extractor.py` | COVERED |
| NFR P50/P95 latencies | `IMPLEMENTATION_PLAN.md` Stage 14 metrics; targets reproduced in `FEATURE_OVERVIEW.md` | COVERED |
| NFR no files on disk | `DESIGN_PATTERNS.md` + smoke test in Stage 13 | COVERED |
| NFR idempotency | `DESIGN_PATTERNS.md` Idempotency key | COVERED |
| NFR Prometheus metrics | `IMPLEMENTATION_PLAN.md` Stage 14 | COVERED |
| NFR circuit breaker | `DESIGN_PATTERNS.md` Circuit breaker, `IMPLEMENTATION_PLAN.md` Stage 10 | COVERED |

---

## Critical Points

These items concentrate the highest implementation and operational risk.

1. **In-memory file handling** (US-10, BR-01). The implementation must never write the file bytes to disk or to any DB column. The Celery task receives a Redis blob ref (with TTL ≤ 300 s) and must explicitly `DEL` the key in `finally`. An audit smoke test in CI fails if any code path under `ingestion/` opens a file handle pointing under `/var/`, `/tmp/`, or any DB write to a `Binary/Bytes` column.
2. **OpenRouter cost ceiling**. The combination of strategy routing (`pypdf` first), partial-failure threshold, circuit breaker, and per-page idempotency keys is the system's defense against runaway cost. Each component must be tested in isolation and together.
3. **PII isolation**. `delivery_target` reaches the database only as `delivery_target_hash`. `source_metadata` is hashed at the boundary. No raw phone or email in logs. CI runs a log-redaction smoke test on a sample request.
4. **Idempotency under network retry**. The submit endpoint must be idempotent against retried requests from the frontend (network reset). Hash deduplication is the primary defense; combined with the rubric-version comparison documented in `_shared/GLOBAL_ASSUMPTIONS.md` §6.
5. **WhatsApp session timeout** via Redis keyspace expiration requires `notify-keyspace-events Ex` enabled in Redis config; the implementation plan flags this in Stage 11.

---

## Open Questions

**[Q-F1-01]: Should F1's transient tables (`contract_submission`, `ocr_job`) inherit `SoftDeleteObject` and `ModelWithTimeStamps`?**
Source: skill `architecture-conventions.md` mandates these for ORM models; PRD_F1 §5 declares the tables explicitly hard-delete on `expires_at < NOW()` and uses `received_at` (not `created_at`) for the receipt timestamp.
Impact: If we apply the mixins blindly, soft-delete adds a `deleted_at` column never used (hard delete is performed by F8 cron); `ModelWithTimeStamps` would add `created_at` and `updated_at` redundant with `received_at`/`processing_started_at`/`processing_completed_at`.
Referenced in: `IMPLEMENTATION_PLAN.md` Stage 5 "Codebase Alignment Rules" note.
Resolution: **Assumed**. Transient tables do not inherit `SoftDeleteObject` or `ModelWithTimeStamps` (the conventions explicitly say "models that DO NOT use the mixin must justify it" and the PRD justification is the explicit cleanup semantics). Persistent business tables (Project, ContractAnalysis, catalogs) DO inherit the mixins. Documented here so reviewers do not flag it.

**[Q-F1-02]: Should each module declare its own ORM models, or should `platform` own all of them?**
Source: Django's `app_label` is per-app; cross-app FK is supported but adds friction with `makemigrations`.
Impact: Two viable approaches: (A) every module declares the models it owns in its own `infrastructure/django/models.py`, even if those FK across apps; (B) `platform` declares all persistent + transient model classes (matching all DDL), and each feature module re-imports them.
Resolution: **Assumed (B)**. The single `platform` app owns the schema for cohesion; each feature's `infrastructure/django/models.py` re-imports the relevant classes for code-locality. Repositories in each feature use the imported model directly. This avoids cross-app circular FK references in migrations and keeps `makemigrations` deterministic. `MIGRATION_MODULES` maps every short label to its own migrations directory; the `ingestion` migrations directory stays empty (the table is owned by `platform`'s migrations).

**[Q-F1-03]: What is the default vision model on OpenRouter?**
Source: PRD_F1 §10 Open Question 1.
Impact: Cost and OCR quality on poorly lit photos.
Resolution: **Assumed default**: `anthropic/claude-sonnet-4`. Configurable via `OCR_VISION_MODEL`. Product can re-evaluate after measuring real-world cost-quality trade-offs.

**[Q-F1-04]: Where does the placeholder project live?**
Source: F1 creates a `ContractAnalysis` stub at submit time before F2 has extracted the project name; the `project_id` FK is `NOT NULL` per F8.
Impact: We need to either (a) make `project_id` nullable (breaks F8 schema) or (b) seed a placeholder project that F1 references and F2 replaces.
Resolution: **Assumed (b)**. F8's bootstrap data migration seeds one row in `project` with `normalized_name='__unknown_pending__'`, `metadata.placeholder=true`. F1's `AnalysisStubRepository.create_stub` uses it. F2 updates `project_id` after extracting the real name.

**[Q-F1-05]: Public manual retry endpoint?**
Source: PRD_F1 §10 Open Question 2.
Impact: Public retry opens cost-abuse surface; internal-only retry leaves no recourse for unlucky users.
Resolution: **Assumed default**: **Internal-only retry** via `POST /v1/internal/submissions/{id}/retry-ocr` with `HasInternalAuthHeader`. The public surface offers no retry — the user resubmits.

**[Q-F1-06]: Rate-limit policy?**
Source: PRD_F1 §10 Open Question 3.
Impact: Defends against floods.
Resolution: **Assumed default**: 5 submissions/h/IP (`BurstSubmitThrottle`), 3 submissions/h/phone hash (`WhatsAppSubmitThrottle`). Configurable.

**[Q-F1-07]: HEIC library choice?**
Source: PRD_F1 §10 Open Question 4.
Impact: `pyheif` (older) vs `pillow-heif` (modern). Both require `libheif` OS package.
Resolution: **Assumed default**: `pillow-heif` integrated into the worker image's `Dockerfile`. Documented.

**[Q-F1-08]: PDFs with JavaScript / interactive forms?**
Source: PRD_F1 §10 Open Question 5.
Impact: Security and processing reliability.
Resolution: **Assumed default**: Reject at validation with `PDF_NOT_SAFE`. PDF safety detection uses `pypdf.PdfReader.is_javascript_present` and `len(reader.get_form_text_fields() or {})` heuristics.

**[Q-F1-09]: Variant detection (near-duplicate contracts)?**
Source: PRD_F1 §10 Open Question 6.
Impact: A reupload with one paragraph changed produces a new analysis (different hash). The PRD says this is acceptable; embedding-similarity detection is deferred to v2.
Resolution: **Assumed default**: Hash-based dedup only at MVP. Documented.

**[Q-F1-10]: Internal queue delivery semantics?**
Source: PRD_F1 §10 Open Question 7.
Impact: Redis Streams provides at-least-once; exactly-once requires DB transaction coordination.
Resolution: **Assumed default**: At-least-once via Redis Streams for the F1→F2 hop; deduplication by `submission_id` plus a `processing_status` guard on the consumer side. For F4 / F5 / F6 / F7, Celery chains coordinated by `analysis_id`.

**[Q-F1-11]: `cost_saver_mode` default?**
Source: PRD_F1 §10 Open Question 8.
Impact: Tesseract-first for images degrades quality on real photos.
Resolution: **Assumed default**: `OFF` (`OCR_COST_SAVER_MODE=false`). Operators can flip in cost emergencies.

**[Q-F1-12]: Internal-auth secret rotation?**
Source: Implied by `HasInternalAuthHeader`.
Impact: Operationally, secret rotation is required quarterly.
Resolution: **Assumed default**: Env var `INTERNAL_AUTH_SECRET`. Rotation is operational, not part of this plan.

---

## Edge Cases to Validate

- A user uploads the same file twice with the order of files reversed (filename A then B vs. B then A) — the hash must match (sort by filename in canonical hash).
- A user uploads a PDF whose first page is blank and pages 2–10 have text — the diagnosis must not stop at page 1; the orchestrator falls back to vision LLM if the first 100 chars are absent on page 1 but pypdf could read the rest.
- A user uploads a HEIC photo from an iPhone with auto-rotation EXIF — Pillow must respect the EXIF rotation before sending to the vision model.
- A WhatsApp user sends a video by mistake (`video/mp4`). The handler must reject the message politely without breaking the session.
- A user submits a PDF protected by an open-password but not by an owner-password — `pypdf.PdfReader` will raise; the diagnosis must capture this and either fail or attempt vision LLM.
- An extremely sparse PDF (one short clause per page across 50 pages) — text is < 500 chars on page 1 but total > 500 across pages. The `min_text_chars` heuristic must be applied to the full PDF, not page 1 alone.
- Concurrent submission of the same file from two browser tabs of the same IP — both reach the service; the second hits the dedup branch because the first creates the row first; both responses point to the same `analysis_id`. We need a unique constraint on `submission_hash + active_rubric_version` (already covered by the lookup logic; the unique index is NOT on `contract_analysis` itself because two different rubric versions are allowed — this is acceptable as a race with eventual consistency).
- Zavu signed URL expires before the worker downloads it — treat as a transient failure for that media; if more than 30% of media expire, fail the submission.
- A WhatsApp user accepts the disclaimer in a previous session that was canceled, then sends a new file without re-accepting — the new session starts in `disclaimer_accepted=false`; the user is asked again.

---

## Risks

| ID | Risk | Level | Mitigation |
|---|---|---|---|
| R-F1-01 | OpenRouter outage | Architecture | Circuit breaker → Tesseract fallback; the system stays functional for native PDFs (`pypdf`) regardless |
| R-F1-02 | Tesseract OS pack missing in worker image | Operations | CI check that runs `tesseract --list-langs` in the worker image and asserts `spa` present |
| R-F1-03 | Redis Streams data loss | Operations | Redis configured with AOF and replicated; the worst case is one submission lost — user can resubmit; idempotency by hash absorbs this |
| R-F1-04 | Zavu signature mismatch caused by header normalization | Integration | Constant-time compare on the raw bytes; documented test against the actual Zavu signing implementation in a contract test |
| R-F1-05 | Cost overrun from a malicious large-PDF submission | Execution | Page cap (80), file size cap (100 MB total / 15 MB per file), per-page timeout, total submission timeout (5 min), rate limit (5/h/IP) — defense in depth |
| R-F1-06 | The "Worker → ProcessSubmissionTask" rename across diagrams may leave dangling alias references | Execution | The cross-validation pass (Step 4) re-reads every diagram |
| R-F1-07 | Race condition: two browsers submit the same file at the same moment | Execution | Dedup check happens inside the same transaction that creates the stub; the second request reads the row created by the first (READ COMMITTED) and falls into the dedup branch |
| R-F1-08 | Per-PRD vs cross-PRD identifier drift | Architecture | `_shared/GLOBAL_ASSUMPTIONS.md` is the single source of truth for canonical defaults; per-feature plans cite it |

---

## Cross-Validation Log

| Iteration | Discrepancies Found | Files Corrected | Details |
|---|---|---|---|
| 1 | 7 | SOLUTION_DIAGRAMS.md, INTERACTION_DIAGRAMS.md, DESIGN_PATTERNS.md, COMPLETE_FLOWS.md, FEATURE_OVERVIEW.md, ENTITY_RELATIONSHIP_DIAGRAM.md, GLOBAL_ASSUMPTIONS.md | Stack flip from FastAPI to Django 5.2 LTS: class names (`SubmissionRouter`→`SubmissionViewSet`, `ZavuWebhookRouter`→`ZavuWebhookView`, `IngestionWorker`→`ProcessSubmissionTask`), file paths (`infrastructure/db`→`infrastructure/django`, `infrastructure/http`→`infrastructure/django`), persistence (SQLAlchemy→Django ORM), migrations (Alembic→Django migrations), queue (`asyncio worker`→`Celery shared_task`). All occurrences updated; diagram aliases re-keyed for consistency. |
| 2 | 0 | — | Re-read pass. No new discrepancies discovered. Field names, types, endpoint paths, command/query names match across all files. |
| 3 | 0 | — | Cross-reference verification: every entity in the ERD appears in at least one sequence diagram; every class in the class diagram has a counterpart in the implementation plan; every endpoint in COMPLETE_FLOWS.md has a row in IMPLEMENTATION_PLAN.md's endpoint table. |
| 4 | 0 | — | Final acceptance pass — clean. |

---

## PRD Alignment Log

| Iteration | PRD Items Checked | Misalignments Found | Corrections Applied | Coverage % |
|---|---|---|---|---|
| 1 | 38 (10 user stories + 14 BRs + 14 other items) | 0 | — | 100% |

All 10 user stories, 14 business rules, the data-model section, the API surface, the integration points, the prompts, and the NFRs from `PRD_F1` are represented in at least one artifact. The eight open questions from PRD_F1 §10 are mirrored verbatim in this file's Open Questions section with assumed defaults.

---

**End of document.**
