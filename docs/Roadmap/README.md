---
project: Casa Segura
doc_type: roadmap_index
status: living
last_updated: 2026-05-16
tags:
  - casa-segura
  - roadmap
---

# Casa Segura — Roadmap Index

This folder is the operational breakdown of the formal PRDs into Epics and Tickets. It is the source of truth for **what gets built and in what order**. The PRDs remain the source of truth for **what the system must do**.

## Source documents

- [[PRD_GENERAL]] — product requirements, user stories, business rules
- [[FEATURES_MAP]] — F1–F8 feature decomposition, dependency graph
- [[RUBRICA_CONTRATO]] — 38-criterion scoring rubric, overrides, weights
- [[BE-SERVICES]] — service-layer architecture v2 (OCR + RAG + DB)
- [[ARCHITECTURE]] — system-level architecture
- [[DOMAIN_MODEL]] — entity definitions
- [[STATUS_RECONCILIATION]] — gap analysis between [[STATUS]] and PRDs

## How tickets relate to PRDs

```
PRD_GENERAL ──► user stories US-01..US-07
   │
   ├──► FEATURES_MAP ──► features F1..F8 (decomposition)
   │                       │
   │                       └──► EPIC-NN (this folder) ──► CS-NNN tickets
   │
   └──► RUBRICA_CONTRATO ──► 38 criteria, 11 overrides (consumed by EPIC-06)
```

Every ticket's `prd_refs` frontmatter cites the section it implements. Acceptance criteria must be testable against that section.

## Parallel execution

For day-to-day pickup, start with the phase-first team index in [phases/README.md](phases/README.md) and the three-engineer coordination view in [PARALLEL_WORK_PLAN.md](PARALLEL_WORK_PLAN.md). Those files organize work into `FE WORK`, `BE WORK`, `INFRA WORK`, and `API / AI CONNECTIONS` lanes while the tickets remain authoritative.

## Epic catalog

| Epic | Name | Feature | Status |
|---|---|---|---|
| [[EPIC-00-foundation]] | Foundation & Tooling | — | Backlog |
| [[EPIC-01-persistence]] | Persistence & Schema | F8 part 1 | Backlog |
| [[EPIC-02-ingestion-ocr]] | Contract Ingestion & OCR | F1 | Done — Phase 1 closed 2026‑05‑16 (see Phase index recap). |
| [[EPIC-03-corpus-rag]] | Legal Corpus & RAG | F3 | Done — Phase 1 closed 2026‑05‑16 (see Phase index recap). |
| [[EPIC-04-classification]] | Classification & Field Extraction | F2 | Backlog (stub) |
| [[EPIC-05-economic-analysis]] | Economic Analysis & Benchmarks | F5 | Backlog (stub) |
| [[EPIC-06-rubric-engine]] | Rubric Engine & Scoring | F4 | Backlog |
| [[EPIC-07-report-generation]] | Report Generation | F6 | Backlog (stub) |
| [[EPIC-08-multichannel-delivery]] | Multi-Channel Delivery | F7 | Backlog |
| [[EPIC-09-retention-privacy]] | Retention & Privacy Jobs | F8 part 2 | Backlog — scheduler contract shipped ([[CS-270]] / [`ADR-0005`](../adr/ADR-0005-retention-job-scheduling.md); execution jobs queued per tickets). |
| [[EPIC-10-frontend]] | Frontend Web App | — | Done |
| [[EPIC-11-observability]] | Observability, Security, Disclaimers | — | Backlog (stub) |
| [[EPIC-12-project-verification]] | Project Verification (Billboard OCR + Form) | — (separate flow) | In progress — guarded Next.js flows + gated Django stubs (see Parallel Work Plan + [`project-verification-fe-be-gates.md`](../guides/project-verification-fe-be-gates.md)). |

## Ticket numbering

Flat `CS-NNN` with reserved blocks per epic so cross-epic moves don't renumber:

| Block | Epic |
|---|---|
| CS-001 – CS-019 | EPIC-00 |
| CS-020 – CS-049 | EPIC-01 |
| CS-050 – CS-079 | EPIC-02 |
| CS-080 – CS-109 | EPIC-03 |
| CS-110 – CS-129 | EPIC-04 |
| CS-130 – CS-149 | EPIC-05 |
| CS-150 – CS-199 | EPIC-06 |
| CS-200 – CS-229 | EPIC-07 |
| CS-230 – CS-269 | EPIC-08 |
| CS-270 – CS-289 | EPIC-09 |
| CS-290 – CS-329 | EPIC-10 |
| CS-330 – CS-349 | EPIC-11 |
| CS-350 – CS-379 | EPIC-12 |

## How to write a good ticket (project conventions)

1. **One ticket = one PR, ideally**. If a ticket needs three engineers across two weeks, split it.
2. **Acceptance criteria are observable.** "Returns 200 with a `Project` payload containing `normalized_name` matching the slug rule" — not "works correctly".
3. **Scope has an explicit `out` list.** What this ticket does NOT do, especially when adjacent improvements look tempting (Rule 3 — surgical changes).
4. **Cite the PRD section in `prd_refs`.** Every ticket points back. Reviewers can verify the AC matches the spec.
5. **BVA on numeric thresholds.** Every numeric rule in [[RUBRICA_CONTRATO]] has boundary values. Acceptance criteria must exercise them. See ticket template for examples.
6. **Test intent, not behavior.** A test must fail if business meaning changes, not just if implementation changes (Rule 9).

## AI assistants & contributors (Claude, Cursor)

When ship-ready work satisfies tickets, update **ticket files first**, then the **owning epic** (`EPIC-*.md`) Definition of done and epic `status`. Phase docs remain navigation-only. Full playbook: **[`AGENTS.md`](../../AGENTS.md)** at repo root. Cursor encodes the same norms under **`.cursor/rules/`** (`ticket-status-hygiene.mdc`, `epic-status-hygiene.mdc`, `phase-roadmap-hygiene.mdc`, `parallel-roadmap-work.mdc`).

## Phases (from [[FEATURES_MAP]] §3)

```
Phase 0  Foundation               EPIC-00, EPIC-01
Phase 1  Input pipelines          EPIC-02, EPIC-03      (parallel)
Phase 2  Contract intelligence    EPIC-04
Phase 3  Analysis                 EPIC-05               (extends EPIC-03)
Phase 4  Evaluation engine        EPIC-06
Phase 5  User output              EPIC-07, EPIC-08
Phase 6  Privacy closure          EPIC-09
Cross    Web, Obs, Project Verif  EPIC-10, EPIC-11, EPIC-12
```
