---
project: Casa Segura
doc_type: phase_index
phase: 1
status: living
last_updated: 2026-05-16
# Phase 1 implementation pass (Pixtral OCR architecture) committed in d613c2d.
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

Phase 1 backend lane is in implementation (commit `d613c2d`):

- ✅ `done`: CS-057 (discard-after-extract invariant).
- 🟡 `in_progress` (code shipped, AC closure pending a live end-to-end run with `OPENROUTER_API_KEY` + an ingested corpus): CS-050/051/052/053/054/055/056/059/060 (EPIC-02) and CS-080/081/082/083/084/085/086/087/088/089/090 (EPIC-03).

The next backend-blocking pickup on this phase is the **live verification pass** — run `python manage.py ingest_corpus --version <date> --activate`, then exercise the `POST /api/v1/submissions/` + `POST /api/v1/corpus/retrieve/` endpoints with a real `OPENROUTER_API_KEY` to flip the `in_progress` tickets to `done`. See [PHASE-1-config-checklist.md](PHASE-1-config-checklist.md).

Out-of-phase pickups still pending:

- ~~CS-058~~ — **done** (BE disclaimer gate + persistence; FE multipart aliases + defaults aligned).
- CS-033 — 38-criterion YAML loader for RubricVersion (Phase 0 → unblocks CS-086 pattern shortcut against real rubric).

## FE WORK

- ~~[CS-058](../tickets/CS-058.md)~~ — **done** (server-side disclaimer enforcement + `/subir` wiring; env defaults align with Django `/api/v1/submissions/`).

FE should keep coordinating disclaimer copy with [CS-291](../tickets/CS-291.md) and [CS-297](../tickets/CS-297.md) in [Cross-Cutting Work](CROSS-cutting.md), keeping Spanish disclaimer copy centralized.

## BE WORK

- [CS-050](../tickets/CS-050.md) - Upload endpoint with format and size validation.
- [CS-051](../tickets/CS-051.md) - Content hash for idempotency.
- [CS-052](../tickets/CS-052.md) - `ocr.detect_kind` routing.
- [CS-053](../tickets/CS-053.md) - Text-PDF extraction with pypdf.
- [CS-054](../tickets/CS-054.md) - Scanned-PDF extraction via vision LLM.
- [CS-055](../tickets/CS-055.md) - Tesseract Spanish fallback path.
- [CS-056](../tickets/CS-056.md) - `not_analyzable` error envelope and reasons.
- [CS-057](../tickets/CS-057.md) - Discard-after-extract invariant and test.
- [CS-059](../tickets/CS-059.md) - Page-count and size caps.
- [CS-060](../tickets/CS-060.md) - Latency budget instrumentation.

## INFRA WORK

- [CS-084](../tickets/CS-084.md) - Transactional ingestion CLI with idempotency.
- [CS-087](../tickets/CS-087.md) - Similarity threshold tuning with eval set.
- [CS-088](../tickets/CS-088.md) - Curated finding/article eval pairs.

Infra/data support should verify pgvector availability, OCR/vision model env configuration, fixtures, and CI hooks before declaring Phase 1 end-to-end runnable in staging.

## API / AI CONNECTIONS

- [CS-080](../tickets/CS-080.md) - Corpus loader for legal sources.
- [CS-081](../tickets/CS-081.md) - Chunk markdown body into LegalChunk segments.
- [CS-082](../tickets/CS-082.md) - Tag and relevance normalization rules.
- [CS-083](../tickets/CS-083.md) - Embedding pipeline.
- [CS-085](../tickets/CS-085.md) - `retrieve_for_finding` API.
- [CS-086](../tickets/CS-086.md) - `pattern_legal_link` shortcut.
- [CS-089](../tickets/CS-089.md) - Per-finding citation tracing.
- [CS-090](../tickets/CS-090.md) - Corpus version stamp on ingestion.

## Parallel Pick Guidance

- BE can take upload/OCR routing, extraction, not-analyzable envelopes, and retention invariants.
- API / AI can take corpus loading, chunking, embeddings, retrieval, and citation tracing.
- Infra supports pgvector checks, model/env variables, latency instrumentation, fixtures, and CI hooks.

