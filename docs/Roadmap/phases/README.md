---
project: Casa Segura
doc_type: phase_index
status: living
last_updated: 2026-05-16
tags:
  - casa-segura
  - roadmap
  - phases
---

# Phase Index

These files are the team pickup layer for the roadmap. Use them to choose work by delivery phase and lane, then open the linked ticket before implementing.

Do not move ticket files out of `docs/Roadmap/tickets/`; those files remain the source of truth for scope, dependencies, acceptance criteria, and status. The overall roadmap contract lives in [Roadmap Index](../README.md).

Use this folder as a phase-first pick list for parallel work:

- [Phase 0 - Foundation and Schema](PHASE-0-foundation-schema.md)
- [Phase 1 - Input Pipelines](PHASE-1-input-pipelines.md)
- [Phase 2 - Contract Intelligence](PHASE-2-contract-intelligence.md)
- [Phase 3 - Economic Analysis](PHASE-3-economic-analysis.md)
- [Phase 4 - Evaluation Engine](PHASE-4-evaluation-engine.md)
- [Phase 5 - User Output](PHASE-5-user-output.md)
- [Phase 6 - Privacy Closure](PHASE-6-privacy-closure.md)
- [Cross-Cutting Work](CROSS-cutting.md)

## Lane Legend

- `FE WORK` - Next.js App Router, mobile UI, Spanish `tú` copy, accessibility, and result/upload surfaces.
- `BE WORK` - Django 5.2 LTS, DRF, Django ORM, domain models, services, workers, report rendering, and tests.
- `INFRA WORK` - CI, env, secrets, deployment, queues, schedulers, observability, security runbooks, and operational ADRs.
- `API / AI CONNECTIONS` - OCR, RAG, prompts, evals, backend/frontend contracts, SMS/email providers, webhooks, and external integrations.

## Current Ready Picks

- [CS-270](../tickets/CS-270.md) - retention scheduler ADR (`ready`; no deps).
- [CS-298](../tickets/CS-298.md) - **Vercel frontend deploy** (`ready`; infra operator connects GitHub → sets `CASASEGURA_API_BASE_URL`; see [`frontend/README.md`](../../frontend/README.md)).
- [CS-299](../tickets/CS-299.md) - physical Android QA at 360px (`ready`; run after Preview/Production URL exists; checklist in `frontend/docs/CS-299-mobile-qa-checklist.md`).

**In flight:** [CS-001](../tickets/CS-001.md) (repo posture and README skeleton) is **`in_progress`**; completing it unblocks **`CS-002`** and **`CS-003`**. EPIC-12 optional verification shells: [CS-356](../tickets/CS-356.md), [CS-351](../tickets/CS-351.md), [CS-355](../tickets/CS-355.md) are **`in_progress`** on the frontend (`PROJECT_VERIFICATION_ENABLED` — see [`frontend/README.md`](../../frontend/README.md)).

Phase pages also include phase-local `Ready Now` notes so engineers can see whether their phase has work available. If the global list changes, update this file and [Parallel Work Plan](../PARALLEL_WORK_PLAN.md) in the same documentation pass.

## Maintenance Notes

- Phase files link to source-of-truth PRDs, domain docs, analysis docs, and ADRs; they do not redefine requirements.
- `Ready Now` sections must reflect ticket frontmatter and dependency state, not preference or priority alone.
- When a ticket's acceptance criteria are met, update that ticket's frontmatter `status` before treating the work as complete.

