---
project: Casa Segura
doc_type: phase_index
phase: 0
status: living
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - phase-0
---

# Phase 0 - Foundation and Schema

Goal: create the repository, **Django/DRF** + web scaffolds, CI/config baseline, and **Postgres 15 + pgvector** persistence layer that every feature epic depends on. See [ADR-0001 — Django backend stack](../../adr/ADR-0001-django-backend-stack.md).

Source epics:

- [EPIC-00 - Foundation & Tooling](../EPIC-00-foundation.md)
- [EPIC-01 - Persistence & Schema](../EPIC-01-persistence.md)

## Ready Now

- [CS-001](../tickets/CS-001.md) - Initialize public repo with MIT license and README skeleton.

## Foundation Tickets

- [CS-001](../tickets/CS-001.md) - Initialize public repo with MIT license and README skeleton.
- [CS-002](../tickets/CS-002.md) - Django 5.2 LTS + DRF scaffold with pyproject, ruff, mypy, pytest.
- [CS-003](../tickets/CS-003.md) - Next.js scaffold with Tailwind, shadcn/ui, ESLint, Prettier.
- [CS-004](../tickets/CS-004.md) - CI pipeline on PR.
- [CS-005](../tickets/CS-005.md) - Pre-commit hooks for API and web.
- [CS-006](../tickets/CS-006.md) - Secrets baseline and env surface.
- [CS-007](../tickets/CS-007.md) - Structured logging with correlation IDs.
- [CS-008](../tickets/CS-008.md) - Health and readiness endpoints.
- [CS-009](../tickets/CS-009.md) - Standard error envelope schema.
- [CS-010](../tickets/CS-010.md) - Versioning ADR.

## Persistence Tickets

- [CS-020](../tickets/CS-020.md) - Provision Postgres 15+ with pgvector.
- [CS-021](../tickets/CS-021.md) - Initial Django migration framework.
- [CS-022](../tickets/CS-022.md) - Django ORM / DB wiring for DRF and workers.
- [CS-023](../tickets/CS-023.md) - Schema: Project entity.
- [CS-024](../tickets/CS-024.md) - Schema: ContractAnalysis entity.
- [CS-025](../tickets/CS-025.md) - Schema: ContractSubmission and OcrJob.
- [CS-026](../tickets/CS-026.md) - Schema: LegalDocument, LegalChunk, CorpusVersion.
- [CS-027](../tickets/CS-027.md) - Schema: Criterion and RubricVersion.
- [CS-028](../tickets/CS-028.md) - Schema: EconomicBenchmark.
- [CS-029](../tickets/CS-029.md) - Schema: DeliveryRequest.
- [CS-030](../tickets/CS-030.md) - DB invariants, checks, enums, indexes.
- [CS-031](../tickets/CS-031.md) - Project name canonicalization.
- [CS-032](../tickets/CS-032.md) - Test fixture infrastructure.
- [CS-033](../tickets/CS-033.md) - Seed RubricVersion catalog.
- [CS-034](../tickets/CS-034.md) - Seed CorpusVersion placeholder.
- [CS-035](../tickets/CS-035.md) - Migration smoke test in CI.

## Parallel Pick Guidance

- Backend starts with [CS-002](../tickets/CS-002.md), then [CS-007](../tickets/CS-007.md), [CS-008](../tickets/CS-008.md), and [CS-009](../tickets/CS-009.md).
- Frontend starts with [CS-003](../tickets/CS-003.md), then [CS-290](../tickets/CS-290.md) from cross-cutting frontend work.
- Infra starts with [CS-006](../tickets/CS-006.md), [CS-004](../tickets/CS-004.md), [CS-005](../tickets/CS-005.md), and [CS-020](../tickets/CS-020.md) as dependencies unlock.

