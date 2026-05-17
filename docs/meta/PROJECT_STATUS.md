---
last_reviewed: 2026-05-17
---

# Casa Segura — project status snapshot (manual)

Hand-curated, low-frequency snapshot aligned with roadmap pickup docs. Prefer [`docs/Roadmap/tickets/`](../Roadmap/tickets/) for authoritative ticket state.

## Shipped highlights

- **Phase 1 input pipelines:** EPIC‑02 (ingestion/OCR) and EPIC‑03 (corpus/RAG) are closed; corpus stack matches calibration notes in roadmap phase index.
- **Phase 3 economic analysis:** EPIC‑05 closed 2026‑05‑17 (CS-130..CS-137). Deterministic F5 pipeline lives in `backend/economics/`: versioned `economic_benchmarks_2026q2.yaml` catalog + seeder/loader, compound rate normalizer (BR-05), French amortization + BR-07 coherence, asymmetric benchmark comparisons (BR-02/BR-11), USD overcost, `EconomicSummary` assembler matching [`ECONOMIC_SUMMARY_CONTRACT.md`](../analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md), byte-equal `benchmark_version` stamping + BR-12 freshness signal, and BR-09 honesty guard. 103 tests, zero LLM calls (BR-13). Pipeline-level wiring (`analyze()` invocation post-classification) deferred until EPIC-04 orchestrator lands.
- **Frontend web:** EPIC‑10 marked done; canonical app lives under `frontend/`.
- **Retention scheduler architecture:** [`CS-270`](../Roadmap/tickets/CS-270.md) landed with [`ADR-0005`](../adr/ADR-0005-retention-job-scheduling.md) (dry-validate CLI + CI guard).
- **EPIC‑12 stubs:** Django DRF stubs under `/api/v1/project-verification/*` gated by backend `PROJECT_VERIFICATION_ENABLED`; App Router flows under `/verificacion-proyecto` gated by frontend flag (both default-off).

## Active lanes

- **EPIC‑12 productisation:** billboard OCR correctness ([`CS-350`](../Roadmap/tickets/CS-350.md)), manual ↔ OCR telemetry/prefills ([`CS-351`](../Roadmap/tickets/CS-351.md)), resultado polish/registry ([`CS-355`](../Roadmap/tickets/CS-355.md)), gate conformance ([`CS-356`](../Roadmap/tickets/CS-356.md)).
- **Foundational repo tickets:** legacy `CS-001` posture work still tracked in roadmap index notes.

## Deferred / risks

- **Retention jobs execution (`CS-271`…`CS-275`):** scheduler contract exists (ADR‑0005) but destructive batch deletes + beat rows remain **explicitly deferred** until persistence/F8 sequencing is prioritized. Implement only after confirming ORM/schema reality in [`backend/platform_core`](../architecture/) and aligning with GDPR-style retention narratives in tickets.
- **FE/BE half-enablement:** mismatched flags intentionally produce obvious errors (demo matrix in [`docs/guides/project-verification-fe-be-gates.md`](../guides/project-verification-fe-be-gates.md)); ops should keep paired env bundles in deployments.
- **Pipeline orchestration for F5:** `economics.application.analyzer.analyze()` is testable in isolation but no production code path invokes it yet. Awaits an EPIC‑04 orchestrator ticket that chains ingestion → classification → economics → rubric → report and persists `ContractAnalysis` rows.
- **Benchmark catalog legal verification:** every row in `backend/fixtures/economic_benchmarks_2026q2.yaml` currently carries `source_status: pending_verification` in its `notes`. Promotion to "official" requires ABANSA / BCR / SSF sign-off (RUBRICA §17 open decision); EPIC-05 ships with provisional seed values.

## Next pickups

- INFRA hygiene: secrets baseline [`CS-006`](../Roadmap/tickets/CS-006.md), CI pipeline [`CS-004`](../Roadmap/tickets/CS-004.md), hooks [`CS-005`](../Roadmap/tickets/CS-005.md), Postgres/pgvector ergonomics [`CS-020`](../Roadmap/tickets/CS-020.md) once foundation tickets close.
- EPIC‑12: advance OCR/manual integration after billboard failure enums ([`CS-350`](../Roadmap/tickets/CS-350.md)) stabilize.
