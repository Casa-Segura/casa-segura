---
id: EPIC-01
name: Persistence & Schema
phase: 0
status: in_progress
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

- [x] Postgres 15+ with `vector` extension running locally via docker-compose (`pgvector/pgvector:pg16`) — managed host pending deployment phase
- [x] Django migrations configured; `python manage.py migrate` builds a fresh DB from zero (CS-021)
- [x] Every entity from [[FEATURES_MAP]] §4 has an ORM model and a migration (CS-025, CS-026, CS-027, CS-028, CS-029)
- [x] CHECK constraints, ENUMs, and indexes enforce the invariants in [[RUBRICA_CONTRATO]] §12 and [[PRD_GENERAL]] BR-04, BR-05, BR-08, BR-16 (CS-026, CS-030 — composite FK, HNSW, GIN, immutability triggers, view checks)
- [/] Project normalization (`canonical_name` → `normalized_name`) is implemented (CS-031 in_progress — function shipped; AC4 service-layer upsert belongs to F2/EPIC-04)
- [/] Test fixtures exist for every entity and the test DB resets cleanly between tests (CS-032 in_progress — factories for 12 entities shipped; per-invariant tests against the factories still pending)
- [/] Seed: `RubricVersion` 0.1 loaded with the 38 criteria catalog from [[RUBRICA_CONTRATO]] §16 (CS-033 in_progress — `seed_rubric_version --activate` loads RubricVersion 1.0.0 with 6 categories A–F; the 38-criterion YAML loader is the remaining gap)
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
