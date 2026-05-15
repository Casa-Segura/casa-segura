---
project: Casa Segura
doc_type: phase_index
phase: 1
status: living
last_updated: 2026-05-15
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

## OCR and Ingestion

- [CS-050](../tickets/CS-050.md) - Upload endpoint with format and size validation.
- [CS-051](../tickets/CS-051.md) - Content hash for idempotency.
- [CS-052](../tickets/CS-052.md) - `ocr.detect_kind` routing.
- [CS-053](../tickets/CS-053.md) - Text-PDF extraction with pypdf.
- [CS-054](../tickets/CS-054.md) - Scanned-PDF extraction via vision LLM.
- [CS-055](../tickets/CS-055.md) - Tesseract Spanish fallback path.
- [CS-056](../tickets/CS-056.md) - `not_analyzable` error envelope and reasons.
- [CS-057](../tickets/CS-057.md) - Discard-after-extract invariant and test.
- [CS-058](../tickets/CS-058.md) - Disclaimer acceptance gate.
- [CS-059](../tickets/CS-059.md) - Page-count and size caps.
- [CS-060](../tickets/CS-060.md) - Latency budget instrumentation.

## Legal Corpus and RAG

- [CS-080](../tickets/CS-080.md) - Corpus loader for legal sources.
- [CS-081](../tickets/CS-081.md) - Chunk markdown body into LegalChunk segments.
- [CS-082](../tickets/CS-082.md) - Tag and relevance normalization rules.
- [CS-083](../tickets/CS-083.md) - Embedding pipeline.
- [CS-084](../tickets/CS-084.md) - Transactional ingestion CLI with idempotency.
- [CS-085](../tickets/CS-085.md) - `retrieve_for_finding` API.
- [CS-086](../tickets/CS-086.md) - `pattern_legal_link` shortcut.
- [CS-087](../tickets/CS-087.md) - Similarity threshold tuning with eval set.
- [CS-088](../tickets/CS-088.md) - Curated finding/article eval pairs.
- [CS-089](../tickets/CS-089.md) - Per-finding citation tracing.
- [CS-090](../tickets/CS-090.md) - Corpus version stamp on ingestion.

## Parallel Pick Guidance

- One BE owner can take upload/OCR routing and extraction.
- One AI/RAG owner can take corpus loading, chunking, embeddings, and retrieval.
- One infra/data owner can support pgvector, env variables, fixtures, telemetry, and CI hooks.

