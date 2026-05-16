---
project: Casa Segura
doc_type: phase_index
phase: 2
status: living
last_updated: 2026-05-16
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

Phase 1 ingestion + corpus retrieval contracts are in place (commit `d613c2d`):

- `POST /api/v1/submissions/` returns `extracted_text_language` + `extracted_text_token_count` per submission, with the text held only in-memory through the extractor (CS-057 invariant — never persisted).
- `LegalCitationService.retrieve_legal_basis(finding=…)` returns ≥0 citations via `POST /api/v1/corpus/retrieve/`.

Phase 2 BE+API tickets are therefore unblocked. The minimum dependency chain is:

1. **CS-110** (classification prompt + few-shot anchors) — entry point; no upstream Phase-2 deps.
2. **CS-114** (classification confidence + extraction field schema) — defines the DTO shape downstream tickets persist.
3. **CS-111** (leasing reclassification detector) — depends on CS-110.
4. **CS-112** (project name normalization + linkage) — depends on CS-031 (Phase-0 in_progress, function shipped) + CS-110.
5. **CS-113** (economic field extraction prompt) — depends on CS-110 + CS-114.
6. **CS-116** (unverifiable bookkeeping for missing fields) — depends on CS-113 + CS-114.
7. **CS-115** (classification eval set) — depends on all five above; ships once they stabilise.

Parallel-safe first picks: **CS-110 + CS-114** (no inter-dep). Once they land, **CS-111**, **CS-112**, **CS-113** can run in parallel.

Upstream notes:

- CS-110 needs a working OpenRouter client + access to extracted text — both shipped in commit `d613c2d` (`shared/llm/openrouter.py`, in-memory text passed by `upload_service.ingest_upload`). The classifier should plug into the same client used by CS-054.
- CS-112's accent/case normalization piggybacks on the function shipped under CS-031 (Phase-0 in_progress); the upsert AC explicitly belongs to this ticket.

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

