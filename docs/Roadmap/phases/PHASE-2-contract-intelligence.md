---
project: Casa Segura
doc_type: phase_index
phase: 2
status: living
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - phase-2
---

# Phase 2 - Contract Intelligence

Goal: classify the contract, extract key fields, normalize project identity, and produce confidence/unverifiable metadata for downstream economics and rubric work.

Source epic:

- [EPIC-04 - Classification & Field Extraction](../EPIC-04-classification.md)

## Tickets

- [CS-110](../tickets/CS-110.md) - Classification prompt and few-shot anchors.
- [CS-111](../tickets/CS-111.md) - Leasing reclassification detector.
- [CS-112](../tickets/CS-112.md) - Project name extraction and normalization.
- [CS-113](../tickets/CS-113.md) - Economic field extraction prompt.
- [CS-114](../tickets/CS-114.md) - Classification confidence and extraction field schema.
- [CS-115](../tickets/CS-115.md) - Classification eval set.
- [CS-116](../tickets/CS-116.md) - Unverifiable bookkeeping for missing fields.

## Parallel Pick Guidance

- AI/RAG owner: prompts, few-shot anchors, leasing reclassification detector, and economic extraction prompt.
- Backend/Data owner: normalized project linkage, confidence schema, and unverifiable payload shape.
- QA owner: eval set coverage across all contract types.

