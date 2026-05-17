---
project: Casa Segura
doc_type: phase_index
phase: 1
status: done
last_updated: 2026-05-16
# Phase 1 closed 2026-05-16. EPIC-03 (Legal Corpus & RAG) shipped with revised
# multi-Top-K AC after four live calibration runs (CS-087). EPIC-02 (Contract
# Ingestion & OCR) all CS-050..CS-060 tickets closed; CS-051 carries a single
# deferred AC (HTTP 409 is_duplicate) blocked by EPIC-04 / EPIC-06 ContractAnalysis
# lookup — explicitly noted in the ticket and the EPIC-02 closure section.
tags:
  - casa-segura
  - roadmap
  - phase-1
---

# Phase 1 - Input Pipelines

Goal: build the contract ingestion/OCR path and the legal corpus/RAG path in parallel after Phase 0 schema basics are available.

Source epics:

- [EPIC-02 - Contract Ingestion & OCR](../EPIC-02-ingestion-ocr.md)
- [EPIC-03 - Legal Corpus & RAG](../EPIC-03-corpus-rag.md)

Source-of-truth links:

- [PHASE-1 configuration checklist](PHASE-1-config-checklist.md) - everything the operator must configure (`.env`, OS deps, Python, docker compose, seeds, smoke checks) for the Phase 1 implementation to run end-to-end.
- [PRD_F1_INGESTA_Y_OCR](../../Casa%20Segura%20Formal%20PRDs/PRD_F1_INGESTA_Y_OCR.md) - upload, OCR, disclaimer gate, and retention expectations.
- [PRD_F3_CORPUS_Y_RAG](../../Casa%20Segura%20Formal%20PRDs/PRD_F3_CORPUS_Y_RAG.md) - legal corpus and retrieval behavior.
- [DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md) - `ContractSubmission`, `OcrJob`, `LegalDocument`, `LegalChunk`, and `CorpusVersion`.
- [F1 analysis plan](../../analysis/F1_ingesta_ocr/IMPLEMENTATION_PLAN.md) - engineering breakdown for ingestion/OCR.
- [F3 analysis plan](../../analysis/F3_corpus_rag/IMPLEMENTATION_PLAN.md) - engineering breakdown for corpus/RAG.

## Ready Now

Phase 1 backend lane status (2026-05-16):

- ✅ `done` (EPIC-03 Legal Corpus & RAG closed): CS-080..CS-090. Architecture is `intfloat/multilingual-e5-large` (1024-dim) + `BAAI/bge-reranker-v2-m3` over top-10 vectorial candidates. Corpus re-authored in Spanish. Final metrics: Strict Top-1 = 0.633, Article-level Top-3 = 0.900, Top-5 = 0.967 (revised AC; trace in CS-087 "Live calibration runs #1–#4").
- ✅ `done`: **EPIC-02 closed 2026-05-16**. CS-050 (multi-file `files[]` 1–50 + image dimensions + batch caps), CS-051 (multi-file SHA-256 composition), CS-052 (router 100-char threshold + `force_strategy`), CS-053 (pypdf separators + normalization + 30s watchdog + 500-char vision escalation), CS-054 (Pixtral single-call), CS-055 (Tesseract mean-confidence gate at 60.0), CS-056 (language gate + HTTP 422), CS-057 (discard-after-extract), CS-058 (disclaimer gate), CS-059 (15 MB byte cap + multi-file aggregation), CS-060 (latency budget instrumentation).
- ✅ EPIC-03 (Legal Corpus & RAG) closed 2026-05-16 — see CS-087 calibration trace.

**Phase 1 closure note** — only deferred AC: CS-051 HTTP 409 `is_duplicate=true` envelope, blocked by [[EPIC-04]] / [[EPIC-06]] ContractAnalysis lookup. Tracked on the CS-051 AC checklist and the EPIC-02 closure section. See [PHASE-1-config-checklist.md](PHASE-1-config-checklist.md) for the operator checklist.

Out-of-phase pickups still pending:

- ~~CS-058~~ — **done** (BE disclaimer gate + persistence; FE multipart aliases + defaults aligned).
- CS-033 — 38-criterion YAML loader for RubricVersion (Phase 0 → unblocks CS-086 pattern shortcut against real rubric).

## FE WORK

- ~~[CS-058](../tickets/CS-058.md)~~ — **done** (server-side disclaimer enforcement + `/subir` wiring; env defaults align with Django `/api/v1/submissions/`).

FE should keep coordinating disclaimer copy with [CS-291](../tickets/CS-291.md) and [CS-297](../tickets/CS-297.md) in [Cross-Cutting Work](CROSS-cutting.md), keeping Spanish disclaimer copy centralized.

## BE WORK

- ~~[CS-050](../tickets/CS-050.md)~~ — **done** (multi-file `files[]` 1–50 + image dimension validator 600×800..8000×10000 + batch caps 100 MB / 80 pages; PRD-canonical error codes `too_many_files` / `total_size_too_large` / `file_too_large` / `image_dimensions_invalid`).
- ~~[CS-051](../tickets/CS-051.md)~~ — **done** (single-file collapses to `sha256(bytes)`; multi-file is `sha256(concat(sorted_by_filename(hexhashes)))`; idempotent re-upload returns existing submission with HTTP 200; HTTP 409 `is_duplicate` AC explicitly deferred to EPIC-04 / EPIC-06).
- ~~[CS-052](../tickets/CS-052.md)~~ — **done** (`ocr.detect_kind` with PRD §US-04 strict `> 100`-char threshold + `force_strategy` override via `X-Force-Strategy` header + BVA at 99/100/101).
- ~~[CS-053](../tickets/CS-053.md)~~ — **done** (pypdf with `--- PAGE N ---` 1-indexed separators + NFKC/CRLF/NBSP/soft-hyphen normalization + 30s per-page wall-clock watchdog + 500-char escalation to vision via orchestrator).
- ~~[CS-054](../tickets/CS-054.md)~~ — **done** (single-call Pixtral via OpenRouter `file-parser` plugin for PDFs + direct `image_url` for images; AC re-anchored to single-call architecture per EPIC-02 audit).
- ~~[CS-055](../tickets/CS-055.md)~~ — **done** (Tesseract Spanish fallback with PRD §US-07 mean-confidence gate at 60.0; `-1` layout placeholders excluded; BVA 59.9/60.0/60.1 covered).
- ~~[CS-056](../tickets/CS-056.md)~~ — **done** (PRD §US-08 language gate over first 2000 chars with strict `> 0.85` confidence + low-confidence warning log; HTTP 422 `LANGUAGE_NOT_SUPPORTED` / `TEXT_TOO_SHORT` envelopes; BVA at 0.849/0.850/0.851 covered).
- [CS-057](../tickets/CS-057.md) - Discard-after-extract invariant and test.
- ~~[CS-059](../tickets/CS-059.md)~~ — **done** (15 MB per-file `OCR_MAX_BYTES` PRD canonical; per-file 50-page cap + combined 80-page aggregate via `_run_batch_extraction` / `_enforce_total_pages`; `.env.example` updated).
- ~~[CS-060](../tickets/CS-060.md)~~ — **done** (`casa_segura_ingest_stage_duration_seconds` + page-bucket histogram `casa_segura_ingest_extract_pages_duration_seconds{strategy,page_bucket}` (1/2-10/11+/unknown) + `casa_segura_ingest_timeouts_total{stage,strategy}` counter; fake-clock CI test verifies bucket increments; cardinality budget called out in metrics.py docstring).

## INFRA WORK

- ~~[CS-084](../tickets/CS-084.md)~~ — **done** (transactional ingestion CLI; CLI flag bug `--version → --corpus-version` patched).
- ~~[CS-087](../tickets/CS-087.md)~~ — **done** with revised multi-Top-K AC after live calibration sweep.
- ~~[CS-088](../tickets/CS-088.md)~~ — **done** (30 cases × 6 categories; `ivu_special` realigned against ES corpus).

Infra/data support should verify pgvector availability, OCR/vision model env configuration, fixtures, and CI hooks before declaring Phase 1 end-to-end runnable in staging.

## API / AI CONNECTIONS

All EPIC-03 tickets closed 2026-05-16:

- ~~CS-080~~ Corpus loader for legal sources — **done**.
- ~~CS-081~~ Chunk markdown body into LegalChunk segments — **done**.
- ~~CS-082~~ Tag and relevance normalization rules — **done**.
- ~~CS-083~~ Embedding pipeline (`intfloat/multilingual-e5-large` + `passage:`/`query:` prefijos) — **done**.
- ~~CS-085~~ `retrieve_for_finding` API (con cross-encoder reranker integrado) — **done**.
- ~~CS-086~~ `pattern_legal_link` shortcut — **done**.
- ~~CS-089~~ Per-finding citation tracing — **done**.
- ~~CS-090~~ Corpus version stamp on ingestion — **done**.

## Parallel Pick Guidance

- BE can take upload/OCR routing, extraction, not-analyzable envelopes, and retention invariants.
- API / AI can take corpus loading, chunking, embeddings, retrieval, and citation tracing.
- Infra supports pgvector checks, model/env variables, latency instrumentation, fixtures, and CI hooks.

