---
project: Casa Segura
doc_type: phase_index
phase: 1
status: living
last_updated: 2026-05-16
# Phase 1 implementation pass (Pixtral OCR architecture) committed in d613c2d.
# EPIC-03 (Legal Corpus & RAG) closed 2026-05-16 with revised multi-Top-K AC after
# four live calibration runs (CS-087). EPIC-02 (Contract Ingestion & OCR) still in_progress;
# CS-052 + CS-054 + CS-055 closed 2026-05-16 (router 100-char threshold + force_strategy
# override; Pixtral single-call AC re-anchor; Tesseract mean-confidence gate at 60.0).
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
- ✅ `done`: CS-052 (`ocr.detect_kind` 100-char threshold + `force_strategy` override), CS-054 (Pixtral single-call extraction — AC re-anchored), CS-055 (Tesseract Spanish fallback mean-confidence gate at 60.0), CS-057 (discard-after-extract invariant), CS-058 (disclaimer gate).
- 🟡 `in_progress` (EPIC-02 Contract Ingestion & OCR — the only remaining blocker for Phase 1 closure): CS-050/051/053/056/059/060.

The next backend-blocking pickup on this phase is **EPIC-02 closure**: ship the CS-053 page separators + 500-char vision retry + 30s timeout, the multi-file upload + image dimension validator (CS-050), wire the PRD US-08 not_analyzable policy (CS-056: first-2000-chars + 0.85 confidence + HTTP 422), enforce page-count caps + 15 MB byte cap (CS-059), and add per-page-bucket latency histograms + fake-clock CI test (CS-060). See [PHASE-1-config-checklist.md](PHASE-1-config-checklist.md).

Out-of-phase pickups still pending:

- ~~CS-058~~ — **done** (BE disclaimer gate + persistence; FE multipart aliases + defaults aligned).
- CS-033 — 38-criterion YAML loader for RubricVersion (Phase 0 → unblocks CS-086 pattern shortcut against real rubric).

## FE WORK

- ~~[CS-058](../tickets/CS-058.md)~~ — **done** (server-side disclaimer enforcement + `/subir` wiring; env defaults align with Django `/api/v1/submissions/`).

FE should keep coordinating disclaimer copy with [CS-291](../tickets/CS-291.md) and [CS-297](../tickets/CS-297.md) in [Cross-Cutting Work](CROSS-cutting.md), keeping Spanish disclaimer copy centralized.

## BE WORK

- [CS-050](../tickets/CS-050.md) - Upload endpoint with format and size validation.
- [CS-051](../tickets/CS-051.md) - Content hash for idempotency.
- ~~[CS-052](../tickets/CS-052.md)~~ — **done** (`ocr.detect_kind` with PRD §US-04 strict `> 100`-char threshold + `force_strategy` override via `X-Force-Strategy` header + BVA at 99/100/101).
- [CS-053](../tickets/CS-053.md) - Text-PDF extraction with pypdf.
- ~~[CS-054](../tickets/CS-054.md)~~ — **done** (single-call Pixtral via OpenRouter `file-parser` plugin for PDFs + direct `image_url` for images; AC re-anchored to single-call architecture per EPIC-02 audit).
- ~~[CS-055](../tickets/CS-055.md)~~ — **done** (Tesseract Spanish fallback with PRD §US-07 mean-confidence gate at 60.0; `-1` layout placeholders excluded; BVA 59.9/60.0/60.1 covered).
- [CS-056](../tickets/CS-056.md) - `not_analyzable` error envelope and reasons.
- [CS-057](../tickets/CS-057.md) - Discard-after-extract invariant and test.
- [CS-059](../tickets/CS-059.md) - Page-count and size caps.
- [CS-060](../tickets/CS-060.md) - Latency budget instrumentation.

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

