---
id: EPIC-01
name: Persistence & Schema
phase: 0
status: done
depends_on:
  - EPIC-00
prd_refs:
  - FEATURES_MAP §4
  - RUBRICA_CONTRATO §12
  - BE-SERVICES §2
  - DOMAIN_MODEL
feature: F8 (part 1)
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-01
---

# EPIC-01 — Persistence & Schema

## Goal

Stand up **Postgres 15** + **pgvector** and define every persistent entity the system needs **before** any service-layer code wants to write rows. This epic owns the data contract: tables, constraints, **Django ORM** models, **Django migrations**, fixtures, and the seed data for the rubric and corpus version catalog. ORM and migration approach: [ADR-0001 — Django backend stack](../adr/ADR-0001-django-backend-stack.md).

This epic does NOT implement retention/anonymization cron jobs — those are [[EPIC-09-retention-privacy]] (F8 part 2). It stands up the schema; the schema enforces the privacy invariants (no contract content columns anywhere) but the jobs that prune are later.

## Definition of done

- [x] Postgres 15+ with `vector` extension running locally via docker-compose (`pgvector/pgvector:pg16`); managed host: **Railway** (Postgres plugin for Django services) with **Neon** (or equivalent) fallback if pgvector is unavailable — documented in [`RAILWAY.md`](../../RAILWAY.md) and root [`README.md`](../../README.md) “Base de datos (Postgres + pgvector)”
- [x] Django migrations configured; `python manage.py migrate` builds a fresh DB from zero (CS-021)
- [x] Every entity from [[FEATURES_MAP]] §4 has an ORM model and a migration (CS-025, CS-026, CS-027, CS-028, CS-029)
- [x] CHECK constraints, ENUMs, and indexes enforce the invariants in [[RUBRICA_CONTRATO]] §12 and [[PRD_GENERAL]] BR-04, BR-05, BR-08, BR-16 (CS-026, CS-030 — composite FK, HNSW, GIN, immutability triggers, view checks)
- [x] Project normalization (`canonical_name` → `normalized_name`) + collision upsert via `ProjectLinker` (CS-031 done — pure normalizer in `platform_core.domain.project_name`; collision/upsert policy in `classification.application.project_linker`; tests in `backend/tests/test_project_name_cs031.py` and `backend/tests/test_project_linker_integration.py` per PR-4 of the EPIC-04 completion plan; service also [[CS-112]])
- [x] Test fixtures exist for every entity and the test DB resets cleanly between tests (CS-032 done — `backend/tests/factories.py`, `conftest.py`; CS-030 retention proofs use `age_to`)
- [x] Seed: `RubricVersion` 1.0.0 loaded with the criteria catalog transcribed from [[RUBRICA_CONTRATO]] §16 (CS-033 done — `seed_rubric_version --activate` bootstraps the version row; `load_rubric_catalog` then idempotently upserts all criteria from `backend/fixtures/rubric_v1.yaml`. Live DB: 42 rows enumerated by the §16 master table; the rubric prose label "38" is a documentation reconciliation follow-up in CS-033)
- [x] Seed: `CorpusVersion` placeholder row exists; actual chunks loaded by [[EPIC-03-corpus-rag]] (CS-034)

## In scope

- Postgres provisioning (local + remote)
- pgvector extension
- Django ORM models and database settings (connections, router if needed)
- Initial Django migration(s) and migration workflow (`makemigrations` / `migrate`)
- Model + migration coverage for every entity in [[FEATURES_MAP]] §4
- DB constraints (CHECK, NOT NULL, UNIQUE, FK, ENUMs)
- Indexes (per-table, including pgvector HNSW or IVFFlat for `legal_chunk.embedding`)
- Project canonicalization logic
- Test fixtures
- Seed scripts for `RubricVersion` and `Criterion`

## Out of scope (explicit)

- Retention cron jobs and anonymization — [[EPIC-09-retention-privacy]]
- Corpus ingestion (chunking, embedding, persisting `legal_chunk` rows) — [[EPIC-03-corpus-rag]]
- Service-layer code that consumes these models — owned by feature epics
- Backup / DR strategy — [[EPIC-11-observability]]
- Connection pool tuning under load — measure first, tune later

## Dependencies

- Blocks: every feature epic that persists state (02–09)
- Blocked by: [[EPIC-00-foundation]]

## Tickets

- [[CS-020]] — Provision Postgres + pgvector (local + remote)
- [[CS-021]] — Initial Django migration framework (per [ADR-0001](../adr/ADR-0001-django-backend-stack.md))
- [[CS-022]] — Django ORM / DB layer wired for DRF and workers (per [ADR-0001](../adr/ADR-0001-django-backend-stack.md))
- [[CS-023]] — Schema: Project entity
- [[CS-024]] — Schema: ContractAnalysis entity
- [[CS-025]] — Schema: ContractSubmission + OcrJob (transient with expires_at)
- [[CS-026]] — Schema: LegalDocument + LegalChunk + CorpusVersion
- [[CS-027]] — Schema: Criterion + RubricVersion
- [[CS-028]] — Schema: EconomicBenchmark
- [[CS-029]] — Schema: DeliveryRequest
- [[CS-030]] — DB invariants: CHECK constraints, ENUMs, indexes (incl. pgvector index)
- [[CS-031]] — Project name canonicalization (slugify + match)
- [[CS-032]] — Test fixture infrastructure (factory pattern)
- [[CS-033]] — Seed RubricVersion 0.1 with 38-criterion catalog
- [[CS-034]] — Seed CorpusVersion placeholder
- [[CS-035]] — Migration smoke test in CI (Django `migrate` forward/backward cycle per ticket AC)

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-01-1 | pgvector not available on Railway free tier | Switch to Supabase (pgvector default). See [[STATUS]] R10. |
| R-01-2 | Schema evolves a lot during EPIC-06 build | Keep migrations granular; one logical change per migration |
| R-01-3 | Project name collision across genuinely-different developments | Normalization rules in [[CS-031]] AC handle accent/case/whitespace; manual dedupe path documented |
| R-01-4 | pgvector index type wrong for our query volume | Start with HNSW; benchmark with realistic corpus size in [[EPIC-03-corpus-rag]] |

## Notes

- [[DOMAIN_MODEL]] is the canonical entity reference
- [[RUBRICA_CONTRATO]] §12.4 lists what is **never** stored — schema must make those columns impossible to add accidentally
- [[BE-SERVICES]] §2.3 reinforces the privacy separation: curated data persists, user data does not
- **CI — migration smoke ([[CS-035]]):** GitHub Actions workflow **`CI`**, job **`Backend migration smoke (CS-035)`** in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) (Postgres 16 + pgvector; forward → `migrate <app> zero` → forward). Branch protection checklist: [`docs/meta/BRANCH_PROTECTION.md`](../meta/BRANCH_PROTECTION.md).
- **EPIC-04 cross-link (2026-05-17):** F2 §5.1 classification + economic-raw columns on `ContractAnalysis` (`classification_confidence`, `classification_attempts`, `elements_detected`, `reclassification_indicators`, `project_name_canonical`, `economic_fields_raw`) land in `platform_core/0005_classification_f2_fields.py` as PR-0 of the [EPIC-04 completion plan](EPIC-04-classification.md). They are owned by EPIC-04 (PRD F2 §5.1) and only listed here so EPIC-01 readers know the schema is no longer frozen at migration `0004`.
