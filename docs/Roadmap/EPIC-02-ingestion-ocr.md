---
id: EPIC-02
name: Contract Ingestion & OCR
phase: 1
status: backlog
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
  - stub
---

# EPIC-02 — Contract Ingestion & OCR

> **Stub.** Epic-level only. Tickets fleshed out in second pass.

## Goal

Receive contract uploads (PDF, JPG, PNG, HEIC, WEBP), detect document kind, extract text using the optimal strategy per [[BE-SERVICES]] §3. Implement [[PRD_GENERAL]] US-01.

## Definition of done

- [ ] `POST /contracts/submit` accepts the five formats listed in US-01
- [ ] `ocr.detect_kind` correctly classifies BILLBOARD_IMAGE / TEXT_PDF / SCANNED_PDF / UNSUPPORTED
- [ ] Text PDFs handled via pypdf; scanned PDFs via vision LLM; Tesseract Spanish as fallback
- [ ] Disclaimer "Esto no es asesoría legal" presented and accepted before processing
- [ ] Failure modes (unreadable, non-Spanish, oversized) return `not_analyzable` with reason
- [ ] Original file discarded immediately after extraction ([[PRD_GENERAL]] BR-01)
- [ ] P95 ingestion+OCR latency under the budget that leaves room for downstream stages (target: <30s of the 90s total in [[PRD_GENERAL]] §5)

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
