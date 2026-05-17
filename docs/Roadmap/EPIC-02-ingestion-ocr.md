---
id: EPIC-02
name: Contract Ingestion & OCR
phase: 1
status: in_progress
depends_on:
  - EPIC-01
prd_refs:
  - PRD_GENERAL US-01
  - FEATURES_MAP §4 (F1)
  - BE-SERVICES §3
feature: F1
owner: tbd
research_refs:
  - GENERATED-RESEARCH-create-ocr-documentation-2026-05-11
tags:
  - casa-segura
  - epic
  - epic-02
---

# EPIC-02 — Contract Ingestion & OCR

## Goal

Receive contract uploads (PDF, JPG, PNG, HEIC, WEBP), detect document kind, extract text using the optimal strategy per [[BE-SERVICES]] §3. Implement [[PRD_GENERAL]] US-01.

## Definition of done

- [ ] `POST /api/v1/submissions/` accepts the five formats listed in US-01 (CS-050 — single-file MVP in place; multi-file 1–50, image dimension validator, PRD-canonical error codes beyond disclaimer still pending; CS-058 **`DISCLAIMER_REQUIRED`** enforced server-side)
- [x] `ocr.detect_kind` routes between pypdf / Pixtral / Tesseract per MIME + native-text probe (CS-052 — **done**: PRD-canonical strict `> 100`-char first-page threshold + `force_strategy` override via `X-Force-Strategy` header + BVA at 99/100/101; multi-file majority logic blocked by CS-050 payload shape)
- [x] Text PDFs handled via pypdf; scanned PDFs and images via Pixtral Large 2411 (OpenRouter, single multimodal model + `file-parser` plugin with `mistral-ocr` engine for PDF); Tesseract Spanish as fallback (CS-053 + CS-054 + CS-055 **done** — pypdf with `--- PAGE N ---` separators + NFKC/CRLF/NBSP/soft-hyphen normalization + 30s wall-clock watchdog + 500-char escalation to vision; single-call Pixtral; Tesseract mean-confidence gate at 60.0)
- [x] Disclaimer "Esto no es asesoría legal" presented and accepted before processing (CS-058 — BE persists `disclaimer_accepted_at` / method and rejects missing acceptance with **`DISCLAIMER_REQUIRED`**; FE `/subir` gate + multipart aliases aligned)
- [x] Failure modes (unreadable, non-Spanish, oversized) return `not_analyzable` with reason (CS-056 — **done**: PRD §US-08 first-2000-chars window + strict `> 0.85` confidence threshold + low-confidence warning log + HTTP 422 `LANGUAGE_NOT_SUPPORTED` / `TEXT_TOO_SHORT` envelopes; `NotAnalyzableReason.TEXT_TOO_SHORT` added for the [[CS-053]] 500-char trigger)
- [x] Original file discarded immediately after extraction ([[PRD_GENERAL]] BR-01); meta-test asserts no model exposes `extracted_text` (CS-057)
- [x] P95 ingestion+OCR latency instrumented per stage with Prometheus histograms against the 90s budget (CS-060 — **done**: `casa_segura_ingest_stage_duration_seconds{stage,strategy}` + page-bucket histogram `casa_segura_ingest_extract_pages_duration_seconds{strategy,page_bucket}` (1/2-10/11+/unknown) + `casa_segura_ingest_timeouts_total{stage,strategy}` counter; fake-clock CI test verifies bucket increments)

## In scope

- Upload endpoint with size limits and content-type allowlist
- `ocr.detect_kind` router
- `ocr.extract_contract_text` with three strategies
- Idempotency by content hash ([[PRD_GENERAL]] §5)
- `ContractSubmission` and `OcrJob` lifecycle

## Out of scope

- Billboard OCR — [[EPIC-12-project-verification]]
- Classification of contract type — [[EPIC-04-classification]]
- Vision LLM client — uses [[EPIC-00-foundation]] LLM gateway

## Tickets (titles only — stubs)

- [[CS-050]] — Upload endpoint with format and size validation
- [[CS-051]] — Content hash for idempotency
- [[CS-052]] — `ocr.detect_kind` router
- [[CS-053]] — Text-PDF extraction via pypdf
- [[CS-054]] — Scanned-PDF extraction via vision LLM (per-page)
- [[CS-055]] — Tesseract Spanish fallback path
- [[CS-056]] — `not_analyzable` error envelope and reasons
- [[CS-057]] — Discard-after-extract invariant + test
- [[CS-058]] — Disclaimer acceptance gate
- [[CS-059]] — Page-count and size caps (`PDF_MAX_PAGES`)
- [[CS-060]] — Latency budget instrumentation

## Notes

- [[GENERATED-RESEARCH-create-ocr-documentation-2026-05-11]] — earlier OCR research (also relevant to [[EPIC-12-project-verification]] for billboard handling)
- [[BE-SERVICES]] §3 routing table is the source of truth for which path each input takes
