---
project: Casa Segura
doc_type: phase_index
status: living
last_updated: 2026-05-17  # Phase 6 EPIC-09 closure; EPIC-06/07 index sync
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

- [CS-001](../tickets/CS-001.md) — **`done`** (2026-05-17) — canonical public repo ([github.com/Casa-Segura/casa-segura](https://github.com/Casa-Segura/casa-segura)), root README + BR-07 posture, commit-signing policy in [`AGENTS.md`](../../../AGENTS.md#commit-signing-policy).
- [[CS-270]](../tickets/CS-270.md) — **`done`** (2026-05-16) — retention scheduler ADR landed; harness + CI documented in [`ADR-0005`](../adr/ADR-0005-retention-job-scheduling.md).
- [EPIC-10 - Frontend Web App](../EPIC-10-frontend.md) - **`done` (2026-05-16).** Deploy + device QA tracked in [CS-298](../tickets/CS-298.md) and [CS-299](../tickets/CS-299.md).

**EPIC-04 (Classification & Field Extraction) cerrada 2026-05-17.** CS-110..CS-116 + CS-031 AC4 → `done`. Pipeline F2 (`backend/classification/application/orchestrator.py::F2Orchestrator`) encadena clasificación + leasing + project + economic + aggregate, persiste en `ContractAnalysis` vía las columnas F2 §5.1 añadidas por `platform_core/0005_classification_f2_fields.py`. Endpoint interno `POST /api/v1/internal/classify` (DRF, `IsInternal`); CI gate `.github/workflows/classification-eval.yml`. Phase 2 cerrada.

**Phase 4–5 closure (2026-05-17):** [[EPIC-06-rubric-engine]] → **`done`** (Definition of done all `[x]`). [[EPIC-07-report-generation]] → **`done`** (canonical HTML/PDF + `/r/` TTL parity via `CS-247`). Remaining **Phase 5** product gap: [[EPIC-08-multichannel-delivery]] **submission-time channel picker** (Epic DoD line 1 — still `[ ]`).

**Phase 6 — EPIC-09:** [[EPIC-09-retention-privacy]](../EPIC-09-retention-privacy.md) → **`done`** (2026-05-17); tickets **`CS-271`**–**`CS-276`** closed — see [Phase 6](PHASE-6-privacy-closure.md). Follow-up (ops / FE): expired-link UX coordination + optional §6.2 audit-row purge automation if not already tracked.

**In flight:** EPIC-12 optional verification work: [CS-356](../tickets/CS-356.md), [CS-351](../tickets/CS-351.md), [CS-355](../tickets/CS-355.md) are **`in_progress`** across `frontend/` and gated Django stubs under `PROJECT_VERIFICATION_ENABLED` (matrix: [`project-verification-fe-be-gates.md`](../../guides/project-verification-fe-be-gates.md)).

**Phase 1 progress (2026-05-16):** EPIC-03 (Legal Corpus & RAG, CS-080..CS-090) closed with revised multi-Top-K AC after four live calibration runs (final: e5-large + bge-reranker-v2-m3 + ES corpus → Strict Top-1 = 0.633, Top-3 = 0.900, Top-5 = 0.967). **Phase 1 closed 2026-05-16.** EPIC-02 (Contract Ingestion & OCR) and EPIC-03 (Legal Corpus & RAG) both `done`. EPIC-02 ships CS-050..CS-060 (multi-file `files[]` 1–50 + image dimensions + batch caps; router 100-char threshold; pypdf separators/normalization/watchdog/vision-escalation; Pixtral single-call; Tesseract mean-confidence gate; PRD §US-08 language gate + HTTP 422; multi-file SHA-256 idempotency; 15 MB byte cap; latency budget instrumentation). One AC deferred to EPIC-04 / EPIC-06: CS-051 HTTP 409 `is_duplicate` envelope (needs ContractAnalysis lookup). See [PHASE-1-input-pipelines.md](PHASE-1-input-pipelines.md).

**Phase 3 closed 2026-05-17:** EPIC-05 (Economic Analysis & Benchmarks, CS-130..CS-137) shipped. Deterministic F5 pipeline lives in `backend/economics/` — versioned benchmark catalog (CS-130), compound rate normalizer (CS-131), monthly-payment ratio bands (CS-132), French amortization + BR-07 coherence (CS-133), asymmetric benchmark comparisons + USD overcost (CS-134), `EconomicSummary` assembler matching [`ECONOMIC_SUMMARY_CONTRACT.md`](../../analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md) (CS-135), byte-equal version stamping + BR-12 freshness signal (CS-136), and BR-09 honesty guard (CS-137). 103 tests, zero LLM calls (PRD_F5 BR-13). Pipeline-level wiring of `analyze()` into a post-classification orchestrator is **deferred** — awaits an EPIC-04 orchestrator ticket. See [PHASE-3-economic-analysis.md](PHASE-3-economic-analysis.md).

Phase pages also include phase-local `Ready Now` notes so engineers can see whether their phase has work available. If the global list changes, update this file and [Parallel Work Plan](../PARALLEL_WORK_PLAN.md) in the same documentation pass.

## Maintenance Notes

- Phase files link to source-of-truth PRDs, domain docs, analysis docs, and ADRs; they do not redefine requirements.
- `Ready Now` sections must reflect ticket frontmatter and dependency state, not preference or priority alone.
- When a ticket's acceptance criteria are met, update that ticket's frontmatter `status` before treating the work as complete.
