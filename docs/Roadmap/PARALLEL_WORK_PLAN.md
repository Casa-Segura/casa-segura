---
project: Casa Segura
doc_type: parallel_work_plan
status: living
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - coordination
---

# Parallel Work Plan

This document turns the roadmap into pickable chunks for a three-engineer team working in parallel on the same repository. The source of truth remains `docs/Roadmap/README.md`, the epic files, and the individual tickets in `docs/Roadmap/tickets/`.

Use this plan to decide who owns which folder, which tickets are safe to start, and which work should wait for a dependency to land.

## Current Snapshot

Only three tickets are marked `ready` right now:

- `CS-001` - Initialize public repo with MIT license and README skeleton.
- `CS-270` - Choose retention job scheduler and document ADR.
- `CS-290` - Build mobile-first landing page.

Most practical implementation work unlocks after `CS-001`, `CS-002`, and `CS-003`:

- `CS-001` unlocks both app scaffolds.
- `CS-002` creates `apps/api`, which unlocks backend, config, logging, database, and CI work.
- `CS-003` creates `apps/web`, which unlocks frontend implementation and web CI.

## Engineer Lanes

### Engineer 1 - Backend Foundation

Primary folders:

- `apps/api/`
- `docs/adr/` when the ADR is backend-facing
- shared backend config files introduced by `CS-002`

Start here:

- `CS-002` - Django 5.2 LTS + DRF API scaffold with `pyproject`, ruff, mypy, pytest (see [ADR-0001](../adr/ADR-0001-django-backend-stack.md)).

Next picks after `CS-002`:

- `CS-007` - Structured logging with correlation IDs and version fields.
- `CS-008` - Health and readiness endpoints.
- `CS-009` - Standard error envelope schema.
- `CS-022` - Django ORM / database layer wired for DRF and workers.

Skill hints:

- Python design patterns for service layering and dependency injection.
- Python error handling for validation, exception mapping, and public error envelopes.
- Python type safety for strict public signatures, **Pydantic v2** domain DTOs and payloads, and Django ORM boundaries.

### Engineer 2 - Frontend Foundation

Primary folders:

- `apps/web/`
- frontend-facing design/token files
- page and component folders introduced by `CS-003`

Start here:

- `CS-003` - Next.js scaffold with Tailwind, shadcn/ui, ESLint, Prettier.

Next picks after `CS-003`:

- `CS-290` - Mobile-first landing page.
- `CS-291` - Upload page with disclaimer gate.
- `CS-292` - Delivery channel selector.
- `CS-293` - Loading state with rotating Spanish reassurance copy.
- `CS-297` - Single-source disclaimer module.

Constraints:

- `CS-290` is marked ready, but implementation needs `apps/web`.
- Keep landing copy focused on contract analysis. Do not make billboard/project verification a prerequisite.
- Maintain Spanish `tú` register and include `Esto no es asesoría legal` where required.

Skill hints:

- Next.js best practices for App Router, server actions, and client/server boundaries.
- TypeScript expert for strict frontend contracts and test setup.
- UI/UX Pro Max and Web Interface Guidelines for mobile-first layout, accessibility, and contrast.

### Engineer 3 - Infra, Config, and Coordination

Primary folders:

- `.github/`
- `.cursor/rules/`
- root config files
- `docs/adr/`
- `docker-compose.yml`
- environment examples and deployment notes

Start here:

- `CS-270` - Retention job scheduler ADR. This is independent and already ready.

Next picks:

- `CS-006` - Secrets baseline and `.env.example`.
- `CS-004` - CI pipeline for API and web.
- `CS-005` - Pre-commit hooks for both apps.
- `CS-020` - Postgres 15+ with pgvector, local and remote notes.

Constraints:

- `CS-004` and `CS-005` should wait until both `CS-002` and `CS-003` define actual tool commands.
- `CS-020` should wait for `CS-002` and `CS-006`, because it needs API env conventions and database URL policy.
- `CS-270` can proceed now because it is an ADR and does not depend on current app folders.

Skill hints:

- Python design patterns for job interface shape if the ADR sketches callable contracts.
- Python error handling for job exit codes and failure semantics.
- Supabase or Neon Postgres skills if the remote pgvector host is selected.

## Today Plan

### Round 1 - Unblock Folders

- One engineer completes or confirms `CS-001`.
- Backend engineer starts `CS-002` and creates `apps/api`.
- Frontend engineer prepares `CS-003` and then creates `apps/web`.
- Infra engineer starts `CS-270` in `docs/adr` with no app dependency.

### Round 2 - Stabilize Shared Contracts

- Backend continues with `CS-007`, `CS-008`, and `CS-009`.
- Frontend continues with `CS-290` once `apps/web` exists.
- Infra starts `CS-006` after `CS-002` chooses env loading and app boot conventions.

### Round 3 - Make CI and Data Work Real

- Infra implements `CS-004` and `CS-005` after API and web scripts exist.
- Infra or data-oriented backend starts `CS-020`.
- Backend starts `CS-022` after database conventions are clear.

## Phase Clusters

### Phase 0 - Foundation and Schema

Own this before feature work:

- Foundation: `CS-001` through `CS-010`.
- Persistence: `CS-020` through `CS-035`.

Recommended split:

- Backend: `CS-002`, `CS-007`, `CS-008`, `CS-009`, `CS-022`.
- Frontend: `CS-003`, then `CS-290` from the cross-cutting frontend epic.
- Infra/Data: `CS-004`, `CS-005`, `CS-006`, `CS-020`, `CS-021`, `CS-035`.

### Phase 1 - Parallel Input Pipelines

These can split after schema basics are in place:

- OCR and ingestion: `CS-050` through `CS-060`.
- Legal corpus and RAG: `CS-080` through `CS-090`.

Recommended split:

- Backend OCR owner: upload, file validation, extraction routing, pypdf, vision, Tesseract, not-analyzable envelopes.
- AI/RAG owner: corpus loader, chunking, tagging, embeddings, retrieval, evals, citation tracing.
- Infra support: model/env variables, pgvector checks, latency instrumentation, CI fixture support.

### Phase 2 - Contract Intelligence

Main tickets:

- Classification and field extraction: `CS-110` through `CS-116`.

Recommended split:

- AI/RAG owner: prompts, few-shot anchors, leasing reclassification detector, economic extraction prompt.
- Backend/Data owner: project name normalization handoff, confidence schemas, unverifiable bookkeeping.
- QA owner: classification eval set.

### Phase 3 - Economic Analysis

Main tickets:

- Economic benchmarks and computations: `CS-130` through `CS-137`.

Recommended split:

- Data/Backend owner: benchmark schema, rate computations, total cost, overcost, summary model.
- QA owner: boundary tests for rates, payment ratios, missing fields, and asymmetric penalty inputs.

### Phase 4 - Rubric Engine

Main tickets:

- Rubric framework, evaluators, synthesis, and BVA tests: `CS-150` through `CS-171`.

Recommended split:

- Backend core owner: schemas, aggregation, applicability, overrides, band assignment, evaluator framework.
- Backend/AI owner: category evaluators and RAG citation wiring.
- QA owner: BVA tests for bands, interest, down payment, overrides, and asymmetric penalty.

### Phase 5 - User Output

Main tickets:

- Report generation: `CS-200` through `CS-210`.
- Multi-channel delivery: `CS-230` through `CS-248`.

Recommended split:

- Backend/report owner: Jinja shell, sections, PDF rendering, mobile HTML QA.
- Delivery owner: Pydantic schemas, dispatcher, queue, retry policy, email, Zavu, webhook, public link route.
- Frontend owner: result page and upload/delivery surface in `CS-291` through `CS-296`.

### Phase 6 - Privacy Closure

Main tickets:

- Retention and privacy jobs: `CS-270` through `CS-276`.

Recommended split:

- Infra owner: scheduler ADR and operational contract.
- Backend/Data owner: cleanup SQL, anonymization, link expiration, recompute project metrics.
- Security/Privacy owner: irreversible anonymization checks and audit rows.

### Cross-Cutting

Frontend:

- `CS-290` through `CS-299`.

Observability and security:

- `CS-330` through `CS-337`.

Optional project verification:

- `CS-350` through `CS-356`.

Project verification is separate from contract analysis. Do not block upload or analysis flows on billboard OCR or project verification.

## Dependency Map

```mermaid
flowchart TD
  cs001["CS-001 Repo posture"] --> cs002["CS-002 API scaffold"]
  cs001 --> cs003["CS-003 Web scaffold"]
  cs002 --> cs006["CS-006 Env baseline"]
  cs002 --> cs007["CS-007 Logging"]
  cs007 --> cs009["CS-009 Error envelope"]
  cs002 --> cs020["CS-020 Postgres pgvector"]
  cs006 --> cs020
  cs002 --> cs022["CS-022 Django ORM"]
  cs003 --> cs290["CS-290 Landing"]
  cs002 --> cs004["CS-004 CI"]
  cs003 --> cs004
  cs002 --> cs005["CS-005 Precommit"]
  cs003 --> cs005
  cs270["CS-270 Scheduler ADR"] --> retentionJobs["CS-271 to CS-276 Retention jobs"]
```

## Pick-Up Rules

- Pick one ticket at a time and claim it before opening a PR.
- Keep one ticket to one PR unless the ticket explicitly requires a split.
- Read the ticket frontmatter before coding, especially `depends_on`, `domain`, and `secondary_domains`.
- Do not start a blocked ticket unless the blocker is stubbed behind an agreed interface and the PR calls out the assumption.
- Stay inside your lane's primary folders unless the ticket explicitly spans domains.
- If a ticket changes an API contract, update or create the corresponding schema/version note before frontend work depends on it.
- If a ticket touches privacy, logging, OCR text, delivery targets, or report content, assume PII leakage is the main failure mode.
- If a ticket touches UI, verify 360px mobile behavior and avoid horizontal scroll.
- If a ticket touches numeric thresholds, add or preserve BVA coverage from the ticket.

## Merge Conflict Avoidance

- Backend and frontend scaffolds should land before CI/pre-commit hardening.
- Do not have multiple engineers edit the same root config file in separate PRs without coordination.
- Defer broad formatting commits until after the first scaffold PRs land.
- Prefer additive docs changes in separate files over rewriting roadmap source files during implementation.
- Keep shared literals such as `Esto no es asesoría legal` in a single module once `CS-297` or `CS-337` lands.

## BE Stack Trace To Keep Visible

The roadmap standardizes on a **Django 5.2 LTS** + **DRF** Python backend ([ADR-0001](../adr/ADR-0001-django-backend-stack.md)):

- Django + DRF and Python 3.11+ in `CS-002` (local dev via `manage.py` conventions).
- **Pydantic v2** domain DTOs / validation in tickets such as `CS-009`, `CS-150`, `CS-230`, and related work (alongside DRF serializers where appropriate).
- **Django ORM** and **Django migrations** in `CS-021` and `CS-022`.
- **Postgres 15** with **pgvector** in `CS-020` and `CS-030`.
- **Redis** for **Celery** brokers/backends and related jobs across foundation and delivery tickets.
- pypdf, OpenRouter vision, and Tesseract for OCR in `CS-052` through `CS-055`.
- sentence-transformers MiniLM embeddings and pgvector retrieval in `CS-083` through `CS-085`.
- Jinja and WeasyPrint for report generation in `CS-200` through `CS-210`.
- **Celery** workers on **Redis** for delivery and async tasks (`CS-233` and dependents).
- Zavu outbound WhatsApp integration in `CS-238` through `CS-244`.

When starting BE work, search for Python, Django, DRF, **Pydantic v2**, Django ORM, Postgres/pgvector, **Redis**/Celery, OCR, RAG, and Zavu skills before implementation.

