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

Source-of-truth links:

- [PRD_F2_CLASIFICACION](../../Casa%20Segura%20Formal%20PRDs/PRD_F2_CLASIFICACION.md) - classification, extraction, confidence, and unverifiable behavior.
- [PRD_GENERAL](../../Casa%20Segura%20Formal%20PRDs/PRD_GENERAL.md) - product-level user stories and business rules.
- [DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md) - contract analysis fields and project identity.
- [F2 analysis plan](../../analysis/F2_clasificacion/IMPLEMENTATION_PLAN.md) - implementation breakdown and flow assumptions.
- [ADR-0001 - Django backend stack](../../adr/ADR-0001-django-backend-stack.md) - backend boundary for services, DTOs, and persistence.

## Ready Now

No Phase 2 tickets are ready yet. Start after Phase 1 ingestion text and corpus retrieval contracts are available.

## FE WORK

No primary FE tickets live in this phase. FE depends on the API contract outputs here for later upload/result experiences in [Cross-Cutting Work](CROSS-cutting.md).

## BE WORK

- [CS-112](../tickets/CS-112.md) - Project name extraction and normalization.
- [CS-114](../tickets/CS-114.md) - Classification confidence and extraction field schema.
- [CS-116](../tickets/CS-116.md) - Unverifiable bookkeeping for missing fields.

## INFRA WORK

- [CS-115](../tickets/CS-115.md) - Classification eval set.

Keep eval fixtures versioned and privacy-safe. Coordinate with CI conventions from Phase 0 before adding expensive model-backed checks.

## API / AI CONNECTIONS

- [CS-110](../tickets/CS-110.md) - Classification prompt and few-shot anchors.
- [CS-111](../tickets/CS-111.md) - Leasing reclassification detector.
- [CS-113](../tickets/CS-113.md) - Economic field extraction prompt.

## Parallel Pick Guidance

- API / AI owns prompts, few-shot anchors, leasing reclassification, and economic extraction.
- BE owns normalized project linkage, confidence schemas, and unverifiable payload shape.
- INFRA WORK owns eval fixtures and coverage across all contract types.

