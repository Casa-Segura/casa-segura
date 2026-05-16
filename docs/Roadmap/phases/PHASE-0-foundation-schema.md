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

- ◐ [CS-001](../tickets/CS-001.md) - Initialize public repo with MIT license and README skeleton. *(2026-05-16: README now links backend README + RAILWAY.md alongside ADR index; 3/5 ACs ticked; remaining ACs are environmental — public repo + commit signing policy.)*

## FE WORK

- ◐ [CS-003](../tickets/CS-003.md) - Next.js scaffold with Tailwind, shadcn/ui, ESLint, Prettier. *(create-next-app + TS + Tailwind 4 + ESLint live; shadcn/ui, Prettier, Vitest pending — another lane is owning the FE.)*

Use this lane to create the web app foundation. Once `apps/web` exists, pick frontend work from [Cross-Cutting Work](CROSS-cutting.md), starting with [CS-290](../tickets/CS-290.md).

## BE WORK

- ☑ [CS-002](../tickets/CS-002.md) - Django 5.2 LTS + DRF scaffold with pyproject, ruff, mypy, pytest. *(2026-05-16: flipped to done — `ruff check .` clean, mypy strict islands clean, docker-compose `api` service uses post-split `Dockerfile.web`. 7/7 ACs.)*
- ☑ [CS-007](../tickets/CS-007.md) - Structured logging with correlation IDs. *(All 5 ACs ticked and re-verified; structlog + middleware + X-Request-ID + error-path correlation + default `rubric_version`/`corpus_version` keys.)*
- ☑ [CS-008](../tickets/CS-008.md) - Health and readiness endpoints. *(`/api/health/` liveness + `/api/ready/` with DB + Redis ping; 503 with reason codes.)*
- ☑ [CS-009](../tickets/CS-009.md) - Standard error envelope schema. *(All 5 ACs ticked; `DomainException` hierarchy + DRF handler + envelope mirrors `X-Request-ID`; root README ships success+failure JSON example.)*
- ☑ [CS-021](../tickets/CS-021.md) - Initial Django migration framework. *(All 5 ACs ticked; Makefile + reverse-migrate CI + `backend/README.md` DB cheatsheet + naming-convention policy.)*
- ◐ [CS-022](../tickets/CS-022.md) - Django ORM / DB wiring for DRF and workers. *(2026-05-16: `ATOMIC_REQUESTS = env.bool("DB_ATOMIC_REQUESTS", default=False)` added to Postgres branch; backend README ships `transaction.atomic` snippet; 4/5 ACs. AC3 (`select_for_update` example endpoint) remains.)*
- ☑ [CS-023](../tickets/CS-023.md) - Schema: Project entity. *(All 5 ACs ticked; `assert_no_pii` walks metadata, `Project.clean()` raises ValidationError, `Project.save()` defaults `last_analyzed`.)*
- ☑ [CS-024](../tickets/CS-024.md) - Schema: ContractAnalysis entity. *(2026-05-16: flipped to done — all 5 ACs verified in code; invariant-test follow-up tracked by CS-032.)*
- ☑ [CS-025](../tickets/CS-025.md) - Schema: ContractSubmission and OcrJob. *(All ACs met; no `extracted_text` column; file_count 1-50 CHECK.)*
- ☑ [CS-026](../tickets/CS-026.md) - Schema: LegalDocument, LegalChunk, CorpusVersion. *(Composite FK `legal_chunk → legal_document` ON DELETE CASCADE landed via `0002_fk_doc_hnsw_immutability`.)*
- ☑ [CS-027](../tickets/CS-027.md) - Schema: Criterion and RubricVersion. *(Composite `(code, rubric_version)` unique + weight/category CHECKs + partial unique `is_active`.)*
- ☑ [CS-028](../tickets/CS-028.md) - Schema: EconomicBenchmark. *(`BenchmarkVersion` + `EconomicBenchmark` with unit CHECK including `ratio` per PRD DDL.)*
- ☑ [CS-029](../tickets/CS-029.md) - Schema: DeliveryRequest. *(All fields, status/channel CHECKs, partial index on `next_attempt_not_before`, target_value_encrypted nullable for purge.)*
- ◐ [CS-031](../tickets/CS-031.md) - Project name canonicalization. *(`platform_core.domain.project_name.normalize_project_name` + F2 algorithm; ticket sample fixed to `"los ebanos"` per ADR-0003; AC4 (upsert collision policy) belongs to the F2 service. 4/5 ACs.)*

## INFRA WORK

- ◐ [CS-004](../tickets/CS-004.md) - CI pipeline on PR. *(`.github/workflows/ci.yml` lint/test/migration-smoke/frontend-build jobs landed; ruff + django-stubs now in pyproject; AC4/AC5 (negative-test + default-branch green) pending first PR run; AC2 waits for FE Vitest. 2/5 ACs.)*
- ◐ [CS-005](../tickets/CS-005.md) - Pre-commit hooks for API and web. *(2026-05-16: `.pre-commit-config.yaml` at repo root wires ruff (check+format) on `backend/**`, prettier --check on `frontend/**`, plus cross-cutting hooks; ESLint + mypy deferred to CI. 3/4 ACs; AC4 needs an actual `pre-commit run --all-files` pass.)*
- ◐ [CS-006](../tickets/CS-006.md) - Secrets baseline and env surface. *(2026-05-16: `.env.example` now ships PDF/OCR/embedding/retention/link-TTL/jobs key surface per PRD F8 §6.3 + BE-SERVICES §9. 4/5 ACs; AC5 needs a clean-clone smoke + settings.py audit for graceful defaults on the new keys.)*
- ☑ [CS-010](../tickets/CS-010.md) - Versioning ADR. *(All 5 ACs ticked; ADR-0004 Accepted; root README ADR index lists ADR-0001/0002/0003/0004.)*
- ◐ [CS-020](../tickets/CS-020.md) - Provision Postgres 15+ with pgvector. *(Local stack via `docker-compose.dev.yml` with `pgvector/pgvector:pg16`; staging/prod provisioning pending.)*
- ◐ [CS-030](../tickets/CS-030.md) - DB invariants, checks, enums, indexes. *(HNSW + `idx_criterion_types` GIN + `reject_catalog_mutation` function + 3 triggers + `v_system_health`/`v_retention_status` views live in `casasegura`; views return finite integers; EXPLAIN-on-seeded-chunks + overdue-fixture ACs still need fixtures. 3/5 ACs.)*
- ◐ [CS-032](../tickets/CS-032.md) - Test fixture infrastructure. *(`conftest.py` + `tests/factories.py` for all 12 entities + `random_vector_384`/`make_public_short_id`/`age_to`/`expire_in` helpers + smoke test landed; negative FK-order example + CI runtime budget pending. 3/5 ACs.)*
- ◐ [CS-035](../tickets/CS-035.md) - Migration smoke test in CI. *(`backend-migration-smoke` job runs forward → all-app zero → forward against `pgvector/pgvector:pg16`; required-status / negative-test / timing / EPIC link pending. 1/5 ACs.)*

## API / AI CONNECTIONS

- ☑ [CS-033](../tickets/CS-033.md) - Seed RubricVersion catalog. *(2026-05-16: flipped to done — `load_rubric_catalog` command loads `backend/fixtures/rubric_v1.yaml` with all 42 criteria from RUBRICA_CONTRATO §16 master table (per-category weights sum to 100). Live-verified idempotent: 1st run created=42, 2nd run updated=42. Headline-number reconciliation (MD prose says 38, table has 42) and `rubric_version` row drift logged as follow-ups.)*
- ☑ [CS-034](../tickets/CS-034.md) - Seed CorpusVersion placeholder. *(All 5 ACs ticked; `seed_corpus_version` idempotent + live row + `backend/corpus/README.md` documents placeholder semantics.)*

Use this lane for the early contracts that later OCR, RAG, rubric, and report work depend on. Keep seed data versioned and traceable to the PRDs and rubric source.

## Parallel Pick Guidance

- Start with `CS-001`. It unlocks both app scaffolds.
- BE should take `CS-002` before service, logging, health, and ORM tickets.
- FE should take `CS-003`, then move to cross-cutting frontend tickets.
- Infra should wait on concrete scaffold commands before hardening CI and pre-commit.

## Open follow-ups to close Phase 0 partials

The 2026-05-15 audit's full closeout list lived here; most of it landed
in the 2026-05-16 batch. What remains:

- **CS-001 AC4/AC5** — environmental (public-repo verification) and policy (commit signing). Not code work.
- **CS-003** — shadcn/ui + Prettier + at least one Vitest smoke test under `frontend/`. Owned by the FE lane.
- **CS-004 AC4/AC5** — pending first PR run against `main` once the branch is configured + the migration smoke job lands a negative test.
- **CS-005 AC4** — actually run `pre-commit run --all-files` and confirm zero issues (deferred — needs `pre-commit install` on a clean clone).
- **CS-006 AC5** — fresh-clone boot smoke + settings.py audit for graceful defaults on the new keys added 2026-05-16.
- **CS-020 staging/prod** — pgvector provisioning beyond local docker compose. Tracked separately.
- **CS-022 AC3** — example endpoint demonstrating `select_for_update` semantics (currently README snippet only).
- **CS-030 AC1/AC4** — EXPLAIN-on-seeded-chunks proof + overdue-fixture rows for `v_retention_status`. Both need fixtures, not new code.
- **CS-031 AC4** — collision/upsert policy belongs to the F2 Project upsert service (Phase 2, CS-112), not this ticket. Documented in ADR-0003.
- **CS-032 AC3/AC5** — FK-order negative example + CI runtime budget assertion. Both block on real test runs.
- **CS-035** — branch protection + negative migration test + EPIC-01 link in the smoke job docs.

The remaining items split cleanly into two buckets: (a) infrastructure
config that lives outside this repo (CS-004 branch, CS-020 staging,
CS-035 branch protection), and (b) test-backed verification deferred per
this iteration (CS-030 AC1/AC4, CS-032 AC3/AC5, CS-005 AC4).

**As of 2026-05-16, Phase 0 has 15 of 26 tickets `done`** (CS-002,
CS-007, CS-008, CS-009, CS-010, CS-021, CS-023, CS-024, CS-025, CS-026,
CS-027, CS-028, CS-029, CS-033, CS-034). The 11 `in_progress` tickets
all have documented gaps that are either out-of-repo (infra: CS-004,
CS-020, CS-035), deferred per this iteration (tests: CS-005 AC4,
CS-030 AC1/AC4, CS-032 AC3/AC5), or scoped elsewhere (CS-031 AC4
belongs to CS-112 in Phase 2).
