---
id: EPIC-03
name: Legal Corpus & RAG
phase: 1
status: backlog
depends_on:
  - EPIC-01
prd_refs:
  - PRD_GENERAL US-04
  - PRD_GENERAL BR-02, BR-03
  - FEATURES_MAP §4 (F3)
  - BE-SERVICES §4
  - RUBRICA_CONTRATO §2.1
feature: F3
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-03
  - stub
---

# EPIC-03 — Legal Corpus & RAG

> **Stub.** Epic-level only. Tickets fleshed out in second pass.

## Goal

Ingest the curated Salvadoran legal corpus from `Casa Segura/RAG Legal context/` into `legal_document` / `legal_chunk` with embeddings, and expose `retrieve_for_finding` returning verbatim citations under "cite or stay silent" discipline ([[PRD_GENERAL]] BR-02, BR-03).

## Definition of done

- [ ] Ingestion script chunks by article and persists `legal_chunk` rows with embeddings
- [ ] Corpus version stamped on every ingestion; analyses record which version they used
- [ ] `retrieve_for_finding(text, pattern_code, top_k)` returns chunks above similarity threshold, empty list otherwise
- [ ] Threshold and `top_k` are config (`RAG_SIMILARITY_THRESHOLD`, `RAG_TOP_K`)
- [ ] Eval set of ≥30 (finding, expected article) pairs spans the 6 rubric categories
- [ ] Tag inference per chunk supports pre-filtering before vector search

## In scope

- Corpus ingestion script
- Chunking by article (one article = one chunk; split if >1500 chars)
- Tag inference (rule-based: compraventa / arrendamiento / plazo / fideicomiso / consumidor / etc.)
- Embedding via `paraphrase-multilingual-MiniLM-L12-v2`
- pgvector similarity search
- `pattern_legal_link` shortcut path
- Eval set + threshold tuning

## Out of scope

- Schema for legal entities — [[EPIC-01-persistence]] CS-026
- Verdict synthesis consuming retrieved chunks — [[EPIC-06-rubric-engine]] CS-165

## Tickets (titles only — stubs)

- [[CS-080]] — Corpus loader for the 7 sources in `RAG Legal context/`
- [[CS-081]] — Chunking heuristic with subsection split
- [[CS-082]] — Tag inference rules
- [[CS-083]] — Embedding pipeline (sentence-transformers)
- [[CS-084]] — Ingestion CLI with idempotency
- [[CS-085]] — `retrieve_for_finding` API
- [[CS-086]] — `pattern_legal_link` shortcut
- [[CS-087]] — Similarity threshold tuning with eval set
- [[CS-088]] — Eval set of ≥30 (finding, expected article) pairs
- [[CS-089]] — Per-finding citation tracing (every cited chunk must be traceable to retrieval call)
- [[CS-090]] — Corpus version stamp on ingestion

## Notes

- [[BE-SERVICES]] §4 is the design spec
- [[RUBRICA_CONTRATO]] sources list (top of doc) names the 7 laws to ingest
- "Cite or stay silent" rule — empty list is correct behavior when nothing meets threshold
