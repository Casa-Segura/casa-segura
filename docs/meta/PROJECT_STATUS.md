---
last_reviewed: 2026-05-17
---

# Casa Segura — project status snapshot (manual)

Hand-curated, low-frequency digest. **`docs/Roadmap/tickets/CS-*.md` frontmatter `status`** and epic **`EPIC-*.md`** Definition of done remain **authoritative**; this page is navigation and narrative only. Maintainer playbook: [`AGENTS.md`](../../AGENTS.md). Coordination overlay: [`docs/Roadmap/PARALLEL_WORK_PLAN.md`](../Roadmap/PARALLEL_WORK_PLAN.md) and [`docs/Roadmap/phases/README.md`](../Roadmap/phases/README.md).

## Shipped highlights

- **Phase 1 input pipelines:** EPIC‑02 (ingestion/OCR) and EPIC‑03 (corpus/RAG) are closed; corpus stack matches calibration notes in roadmap phase index.
- **Phase 3 economic analysis:** EPIC‑05 closed 2026‑05‑17 (CS-130..CS-137). Deterministic F5 pipeline lives in `backend/economics/`: versioned `economic_benchmarks_2026q2.yaml` catalog + seeder/loader, compound rate normalizer (BR-05), French amortization + BR-07 coherence, asymmetric benchmark comparisons (BR-02/BR-11), USD overcost, `EconomicSummary` assembler matching [`ECONOMIC_SUMMARY_CONTRACT.md`](../analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md), byte-equal `benchmark_version` stamping + BR-12 freshness signal, and BR-09 honesty guard. 103 tests, zero LLM calls (BR-13). Pipeline-level wiring (`analyze()` invocation post-classification) deferred until EPIC-04 orchestrator lands.
- **Frontend web:** EPIC‑10 marked done; canonical app lives under `frontend/`.
- **Retention scheduler architecture:** [`CS-270`](../Roadmap/tickets/CS-270.md) landed with [`ADR-0005`](../adr/ADR-0005-retention-job-scheduling.md) (dry-validate CLI + CI guard).
- **EPIC‑12 optional verification:** billboard vision + deterministic synthesis + guarded reputation lookups + resultado flash UX under `frontend/src/app/verificacion-proyecto/` (`PROJECT_VERIFICATION_ENABLED` mirrored server-side); tickets **`CS-350`–`CS-356`** → `done` (gates in [`docs/guides/project-verification-fe-be-gates.md`](../guides/project-verification-fe-be-gates.md)).

## Phases ([FEATURES_MAP](../Casa%20Segura%20Formal%20PRDs/FEATURES_MAP.md) §3)

Phase pages are pickup/navigation layers; ticket files carry scope and acceptance criteria.

|   Phase   | Theme                           | Owning epic(s) (headline)                         | Index / detail                                                                           |
| :-------: | :------------------------------ | :------------------------------------------------ | :--------------------------------------------------------------------------------------- |
|   **0**   | Foundation & schema             | EPIC‑00 · EPIC‑01                                 | [`PHASE-0-foundation-schema.md`](../Roadmap/phases/PHASE-0-foundation-schema.md)         |
|   **1**   | Input pipelines (parallel)      | **EPIC‑02** · **EPIC‑03** (**done**, 2026‑05‑16)  | [`PHASE-1-input-pipelines.md`](../Roadmap/phases/PHASE-1-input-pipelines.md)             |
|   **2**   | Contract intelligence           | EPIC‑04                                           | [`PHASE-2-contract-intelligence.md`](../Roadmap/phases/PHASE-2-contract-intelligence.md) |
|   **3**   | Economic analysis               | **EPIC‑05** (**done**, 2026‑05‑17; CS‑130–CS‑137) | [`PHASE-3-economic-analysis.md`](../Roadmap/phases/PHASE-3-economic-analysis.md)         |
|   **4**   | Evaluation / rubric             | EPIC‑06                                           | [`PHASE-4-evaluation-engine.md`](../Roadmap/phases/PHASE-4-evaluation-engine.md)         |
|   **5**   | User output                     | EPIC‑07 · EPIC‑08                                 | [`PHASE-5-user-output.md`](../Roadmap/phases/PHASE-5-user-output.md)                     |
|   **6**   | Privacy closure                 | EPIC‑09                                           | [`PHASE-6-privacy-closure.md`](../Roadmap/phases/PHASE-6-privacy-closure.md)             |
| **Cross** | Web, observability, optional PV | EPIC‑10 · EPIC‑11 · EPIC‑12                       | [`CROSS-cutting.md`](../Roadmap/phases/CROSS-cutting.md)                                 |

## Epics at a glance

Canonical catalog lives in [`docs/Roadmap/README.md`](../Roadmap/README.md#epic-catalog). Linked epic specs:

|  Epic   | Spec                                                                           | Feature / scope                          | Snapshot (high level)                                                                                                  |
| :-----: | :----------------------------------------------------------------------------- | :--------------------------------------- | :--------------------------------------------------------------------------------------------------------------------- |
| EPIC‑00 | [`EPIC-00-foundation`](../Roadmap/EPIC-00-foundation.md)                       | Foundation & tooling                     | Backlog                                                                                                                |
| EPIC‑01 | [`EPIC-01-persistence`](../Roadmap/EPIC-01-persistence.md)                     | Persistence & schema (F8 p1)             | Backlog                                                                                                                |
| EPIC‑02 | [`EPIC-02-ingestion-ocr`](../Roadmap/EPIC-02-ingestion-ocr.md)                 | Contract ingestion / OCR (**F1**)        | **Phase 1 closed** · ticket band **CS‑050–CS‑079**                                                                     |
| EPIC‑03 | [`EPIC-03-corpus-rag`](../Roadmap/EPIC-03-corpus-rag.md)                       | Corpus & RAG (**F3**)                    | **Phase 1 closed** · ticket band **CS‑080–CS‑109**                                                                     |
| EPIC‑04 | [`EPIC-04-classification`](../Roadmap/EPIC-04-classification.md)               | Classification (**F2**)                  | Backlog (stub)                                                                                                         |
| EPIC‑05 | [`EPIC-05-economic-analysis`](../Roadmap/EPIC-05-economic-analysis.md)         | Economic analysis (**F5**)               | **Phase 3 economics closed · CS‑130–CS‑137**; production `analyze()` wiring awaits EPIC‑04 orchestrator (see Deferred) |
| EPIC‑06 | [`EPIC-06-rubric-engine`](../Roadmap/EPIC-06-rubric-engine.md)                 | Rubric engine (**F4**)                   | Backlog                                                                                                                |
| EPIC‑07 | [`EPIC-07-report-generation`](../Roadmap/EPIC-07-report-generation.md)         | Reports (**F6**)                         | Backlog (stub)                                                                                                         |
| EPIC‑08 | [`EPIC-08-multichannel-delivery`](../Roadmap/EPIC-08-multichannel-delivery.md) | Delivery (**F7**)                        | Backlog                                                                                                                |
| EPIC‑09 | [`EPIC-09-retention-privacy`](../Roadmap/EPIC-09-retention-privacy.md)         | Retention & privacy (**F8 p2**)          | **ADR + scheduler groundwork** (**CS‑270** `done`); execution jobs **`CS‑271`–`CS‑275`** not started here              |
| EPIC‑10 | [`EPIC-10-frontend`](../Roadmap/EPIC-10-frontend.md)                           | Frontend web app                         | **`done`** (deploy + QA: **CS‑298**, **CS‑299**)                                                                       |
| EPIC‑11 | [`EPIC-11-observability`](../Roadmap/EPIC-11-observability.md)                 | Observability · security · disclaimers   | Backlog (stub) · ticket band **CS‑330–CS‑349**                                                                         |
| EPIC‑12 | [`EPIC-12-project-verification`](../Roadmap/EPIC-12-project-verification.md)   | Optional billboard / manual verification | **`done` · 2026‑05‑17 · CS‑350–CS‑356** (vision OCR, permit/reputation/synthesis stack, resultado flash UX — matrix [`project-verification-fe-be-gates.md`](../guides/project-verification-fe-be-gates.md)) |

**Ticket numbering ↔ epic ownership** — same mapping as roadmap index (`CS‑001–019` → EPIC‑00 … `CS‑350–379` → EPIC‑12).

## Tickets highlighted in this review

Grouped for reading order; **open each ticket** for current `depends_on`, AC, and `status`.

### EPIC‑05 economics closure (ticket band CS‑130–CS‑137)

|                                     Ticket span                                     | Epic    | Snapshot                                                                                                                                                                                               |
| :---------------------------------------------------------------------------------: | :------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [`CS‑130`](../Roadmap/tickets/CS-130.md) … [`CS‑137`](../Roadmap/tickets/CS-137.md) | EPIC‑05 | **`done`** · deterministic economics pipeline shipped 2026‑05‑17 (benchmarks YAML, loaders, assembler, stamping, BR guards); **`analyze()` invocation in prod path** deferred to EPIC‑04 orchestrator. |

### Foundation & infra

|                  Ticket                  | Epic / lane | Role in snapshot                                                            |
| :--------------------------------------: | :---------- | :-------------------------------------------------------------------------- |
| [`CS-001`](../Roadmap/tickets/CS-001.md) | EPIC‑00     | **`done`** · repo público, README/BR-07, política de firmado en `AGENTS.md` |
| [`CS-002`](../Roadmap/tickets/CS-002.md) | EPIC‑00     | **`backend/`** scaffold                                                     |
| [`CS-003`](../Roadmap/tickets/CS-003.md) | EPIC‑00     | **`frontend/`** scaffold                                                    |
| [`CS-004`](../Roadmap/tickets/CS-004.md) | INFRA       | CI pipeline — waits on concrete FE/BE tool commands                         |
| [`CS-005`](../Roadmap/tickets/CS-005.md) | INFRA       | Pre-commit hooks — same sequencing as **CS‑004**                            |
| [`CS-006`](../Roadmap/tickets/CS-006.md) | INFRA       | Secrets baseline / `.env` hygiene                                           |
| [`CS-020`](../Roadmap/tickets/CS-020.md) | EPIC‑01     | Postgres 15 + pgvector — tied to env conventions                            |

### Frontend delivery (closed epic, residual QA docs)

|                  Ticket                  | Epic              | Role in snapshot                |
| :--------------------------------------: | :---------------- | :------------------------------ |
| [`CS-297`](../Roadmap/tickets/CS-297.md) | EPIC‑10 · EPIC‑11 | Single-source disclaimer module |
| [`CS-298`](../Roadmap/tickets/CS-298.md) | EPIC‑10           | Vercel / preview deploy posture |
| [`CS-299`](../Roadmap/tickets/CS-299.md) | EPIC‑10           | Physical device QA checklist    |

### Retention & scheduling (architecture vs execution)

|                                       Ticket                                        | Epic    | Role in snapshot                                                               |
| :---------------------------------------------------------------------------------: | :------ | :----------------------------------------------------------------------------- |
|                      [`CS-270`](../Roadmap/tickets/CS-270.md)                       | EPIC‑09 | Retention scheduler **ADR + harness** — snapshot treats as **`done`**          |
|              [`ADR-0005`](../adr/ADR-0005-retention-job-scheduling.md)              | EPIC‑09 | Celery Beat / job entry contracts                                              |
| [`CS-271`](../Roadmap/tickets/CS-271.md) … [`CS-275`](../Roadmap/tickets/CS-275.md) | EPIC‑09 | **Deferred in this snapshot** until F8 persistence priorities and model review |

### EPIC‑12 optional project verification (CS‑350–CS‑356)

| Ticket span | Snapshot |
| :--- | :--- |
| [`CS-350`](../Roadmap/tickets/CS-350.md) … [`CS-356`](../Roadmap/tickets/CS-356.md) | **`done` (2026‑05‑17)** · billboard vision extraction · OCR→manual parity · SSRF‑guarded reputation · deterministic verdict synthesis · resultado flash UX · mirrored gates ([`project-verification-fe-be-gates.md`](../guides/project-verification-fe-be-gates.md)). |

Implementation pointers: `frontend/src/app/verificacion-proyecto/`, `backend/project_verification/`.

## Active lanes

- **Foundational repo tickets:** CI/secrets/postgres ergonomics ([`CS-004`](../Roadmap/tickets/CS-004.md) … [`CS-020`](../Roadmap/tickets/CS-020.md)) remain active lanes once unblocked.

## Deferred / risks

- **Retention jobs execution (`CS-271`…`CS-275`):** scheduler contract exists (ADR‑0005) but destructive batch deletes + beat rows remain **explicitly deferred** until persistence/F8 sequencing is prioritized. Implement only after confirming ORM/schema reality in [`backend/platform_core`](../architecture/) and aligning with GDPR-style retention narratives in tickets.
- **FE/BE half-enablement:** mismatched flags intentionally produce obvious errors (demo matrix in [`docs/guides/project-verification-fe-be-gates.md`](../guides/project-verification-fe-be-gates.md)); ops should keep paired env bundles in deployments.
- **Pipeline orchestration for F5:** `economics.application.analyzer.analyze()` is testable in isolation but no production code path invokes it yet. Awaits an EPIC‑04 orchestrator ticket that chains ingestion → classification → economics → rubric → report and persists `ContractAnalysis` rows.
- **Benchmark catalog legal verification:** every row in `backend/fixtures/economic_benchmarks_2026q2.yaml` currently carries `source_status: pending_verification` in its `notes`. Promotion to "official" requires ABANSA / BCR / SSF sign-off (RUBRICA §17 open decision); EPIC-05 ships with provisional seed values.

## Next pickups

- INFRA hygiene: secrets baseline [`CS-006`](../Roadmap/tickets/CS-006.md), CI pipeline [`CS-004`](../Roadmap/tickets/CS-004.md), hooks [`CS-005`](../Roadmap/tickets/CS-005.md), Postgres/pgvector ergonomics [`CS-020`](../Roadmap/tickets/CS-020.md) once foundation tickets close.
