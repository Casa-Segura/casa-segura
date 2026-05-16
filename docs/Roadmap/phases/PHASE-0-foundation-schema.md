---
project: Casa Segura
doc_type: phase_index
phase: 0
status: living
last_updated: 2026-05-16
tags:
  - casa-segura
  - roadmap
  - phase-0
---

# Phase 0 - Foundation and Schema

Goal: create the repository, **Django/DRF** + web scaffolds, CI/config baseline, and **Postgres 15 + pgvector** persistence layer that every feature epic depends on.

Status legend: ☑ done · ◐ in progress · ☐ backlog · ✗ blocked/cut. Click each ticket for the per-AC implementation evidence under "Status — 2026-05-15".

Source epics:

- [EPIC-00 - Foundation & Tooling](../EPIC-00-foundation.md)
- [EPIC-01 - Persistence & Schema](../EPIC-01-persistence.md)

Source-of-truth links:

- [Roadmap contract](../README.md) - tickets remain authoritative for status, dependencies, and acceptance criteria.
- [FEATURES_MAP](../../Casa%20Segura%20Formal%20PRDs/FEATURES_MAP.md) - phase sequence and F1-F8 dependency graph.
- [DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md) - canonical entities and persistence boundaries.
- [GLOBAL_ASSUMPTIONS](../../analysis/_shared/GLOBAL_ASSUMPTIONS.md) - shared stack and module assumptions.
- [ADR-0001 - Django backend stack](../../adr/ADR-0001-django-backend-stack.md) - Django/DRF, ORM, migrations, Celery/Redis, and pgvector boundary.
- [ADR-0002 - Rename `platform/` → `platform_core/`](../../adr/ADR-0002-rename-platform-module-to-platform_core.md) - stdlib collision fix.
- [ADR-0003 - CS-031 algorithm divergence](../../adr/ADR-0003-cs031-project-name-normalization-divergence.md) - normalization follows F2 over CS-031 sample.

## Ready Now

- ◐ [CS-001](../tickets/CS-001.md) - Initialize public repo with MIT license and README skeleton. *(LICENSE + .gitignore landed; README skeleton pending.)*

## FE WORK

- ◐ [CS-003](../tickets/CS-003.md) - Next.js scaffold with Tailwind, shadcn/ui, ESLint, Prettier. *(create-next-app + TS + Tailwind 4 + ESLint live; shadcn/ui, Prettier, Vitest pending — another lane is owning the FE.)*

Use this lane to create the web app foundation. Once `apps/web` exists, pick frontend work from [Cross-Cutting Work](CROSS-cutting.md), starting with [CS-290](../tickets/CS-290.md).

## BE WORK

- ◐ [CS-002](../tickets/CS-002.md) - Django 5.2 LTS + DRF scaffold with pyproject, ruff, mypy, pytest. *(Dockerfile multi-stage + ruff.toml + mypy.ini + .python-version + smoke pytest landed; `ruff` / `django-stubs` still missing from pyproject deps; no `api` service in docker-compose.)*
- ☑ [CS-007](../tickets/CS-007.md) - Structured logging with correlation IDs. *(All 5 ACs ticked; structlog + middleware + X-Request-ID + error-path correlation + version fields verified.)*
- ☑ [CS-008](../tickets/CS-008.md) - Health and readiness endpoints. *(`/api/health/` liveness + `/api/ready/` with DB + Redis ping; 503 with reason codes.)*
- ◐ [CS-009](../tickets/CS-009.md) - Standard error envelope schema. *(`DomainException` hierarchy + DRF handler emitting `{error_code, message, details, correlation_id, schema_version}`; README example pending.)*
- ◐ [CS-021](../tickets/CS-021.md) - Initial Django migration framework. *(`migrate` clean on Postgres + Makefile targets + reverse-migrate CI; README DB cheatsheet + naming convention doc pending.)*
- ◐ [CS-022](../tickets/CS-022.md) - Django ORM / DB wiring for DRF and workers. *(Postgres `psycopg2-binary` + `CONN_MAX_AGE` + `CONN_HEALTH_CHECKS`; `django-stubs` missing from deps so mypy strict pass blocked.)*
- ☑ [CS-023](../tickets/CS-023.md) - Schema: Project entity. *(All 5 ACs ticked; `assert_no_pii` walks metadata, `Project.clean()` raises ValidationError, `Project.save()` defaults `last_analyzed`.)*
- ◐ [CS-024](../tickets/CS-024.md) - Schema: ContractAnalysis entity. *(All 5 ACs satisfied; verification tests pending CS-032.)*
- ☑ [CS-025](../tickets/CS-025.md) - Schema: ContractSubmission and OcrJob. *(All ACs met; no `extracted_text` column; file_count 1-50 CHECK.)*
- ☑ [CS-026](../tickets/CS-026.md) - Schema: LegalDocument, LegalChunk, CorpusVersion. *(Composite FK `legal_chunk → legal_document` ON DELETE CASCADE landed via `0002_fk_doc_hnsw_immutability`.)*
- ☑ [CS-027](../tickets/CS-027.md) - Schema: Criterion and RubricVersion. *(Composite `(code, rubric_version)` unique + weight/category CHECKs + partial unique `is_active`.)*
- ☑ [CS-028](../tickets/CS-028.md) - Schema: EconomicBenchmark. *(`BenchmarkVersion` + `EconomicBenchmark` with unit CHECK including `ratio` per PRD DDL.)*
- ☑ [CS-029](../tickets/CS-029.md) - Schema: DeliveryRequest. *(All fields, status/channel CHECKs, partial index on `next_attempt_not_before`, target_value_encrypted nullable for purge.)*
- ◐ [CS-031](../tickets/CS-031.md) - Project name canonicalization. *(`platform_core.domain.project_name.normalize_project_name` + F2 algorithm; ticket sample copy needs update per ADR-0003.)*

## INFRA WORK

- ☐ [CS-004](../tickets/CS-004.md) - CI pipeline on PR. *(Not started; blocks CS-035.)*
- ☐ [CS-005](../tickets/CS-005.md) - Pre-commit hooks for API and web. *(Not started.)*
- ☐ [CS-006](../tickets/CS-006.md) - Secrets baseline and env surface. *(`backend/.env` exists for local dev; no `.env.example`, no secrets ADR.)*
- ☐ [CS-010](../tickets/CS-010.md) - Versioning ADR. *(Not authored; `schema_version="1.0.0"` is hard-coded in `shared/observability/logging.py` pending ADR.)*
- ◐ [CS-020](../tickets/CS-020.md) - Provision Postgres 15+ with pgvector. *(Local stack via `docker-compose.dev.yml` with `pgvector/pgvector:pg16`; staging/prod provisioning pending.)*
- ◐ [CS-030](../tickets/CS-030.md) - DB invariants, checks, enums, indexes. *(Enum CHECKs, GIN, partial uniques live; HNSW on `legal_chunk.embedding`, `reject_catalog_mutation` trigger, and `v_system_health` / `v_retention_status` views pending.)*
- ☐ [CS-032](../tickets/CS-032.md) - Test fixture infrastructure. *(No `tests/`, no `conftest.py`, no factories; blocks invariant tests for CS-023/CS-024/CS-026 and seeds for CS-033/CS-034.)*
- ☐ [CS-035](../tickets/CS-035.md) - Migration smoke test in CI. *(Blocked by CS-004.)*

## API / AI CONNECTIONS

- ☐ [CS-033](../tickets/CS-033.md) - Seed RubricVersion catalog. *(`rubric_version` + `criterion` tables empty.)*
- ☐ [CS-034](../tickets/CS-034.md) - Seed CorpusVersion placeholder. *(`corpus_version` empty.)*

Use this lane for the early contracts that later OCR, RAG, rubric, and report work depend on. Keep seed data versioned and traceable to the PRDs and rubric source.

## Parallel Pick Guidance

- Start with `CS-001`. It unlocks both app scaffolds.
- BE should take `CS-002` before service, logging, health, and ORM tickets.
- FE should take `CS-003`, then move to cross-cutting frontend tickets.
- Infra should wait on concrete scaffold commands before hardening CI and pre-commit.

## Open follow-ups to close Phase 0 partials

The audit on 2026-05-15 surfaced these closeout items. Each maps to one or more partial tickets above.

- Author root `README.md` covering purpose, BR-07 disclaimer, PRD links, error-contract example, DB ops, ADR index — unblocks CS-001 / CS-007 / CS-009 / CS-020.
- Publish `backend/.env.example` listing the full PRD F8 / F1 / F3 env surface — CS-006.
- Add `tests/` tree + `conftest.py` + `factory_boy` factories with a `dim-384` vector helper — CS-032; in turn unblocks per-entity invariant tests for CS-023/CS-024/CS-026 and seeds for CS-033/CS-034.
- Add `Dockerfile` for backend, an `api` service in `docker-compose.dev.yml`, and `.python-version` — CS-002.
- Add `ruff` + `django-stubs` + `mypy.ini` (or update CS-002 to reflect the adopted `black + isort` toolchain) — CS-002.
- Initialize shadcn/ui + Prettier in `frontend/`, add at least one Vitest smoke test, and ensure placeholder copy is BR-07-safe — CS-003.
- Author `.pre-commit-config.yaml` wiring black/isort/mypy + ESLint/Prettier — CS-005.
- Author `.github/workflows/ci.yml` with backend + frontend jobs — CS-004; unblocks CS-035 (migrate→zero→migrate smoke job).
- Author `ADR-0004-versioning.md` covering `schema_version` + rubric/corpus/benchmark bump rules and catalog immutability — CS-010.
- New `corpus` migration creating HNSW index on `legal_chunk.embedding (vector_cosine_ops)` and GIN on `criterion.applicable_types`; migration creating `reject_catalog_mutation` trigger; migration creating `v_system_health` + `v_retention_status` views — CS-030.
- Decide on `legal_chunk.law_id → legal_document.law_id` FK + CASCADE policy or update PRD DDL — CS-026.
- Add PII-guard validator on `Project.metadata` and `last_analyzed` default-on-insert path — CS-023.
- Author idempotent seed commands for rubric `1.0.0` (38 criteria) and placeholder `corpus_version` — CS-033, CS-034 (depend on CS-032).
- Update CS-031 acceptance example to `"los ebanos"` per ADR-0003 in the next ticket grooming pass.
