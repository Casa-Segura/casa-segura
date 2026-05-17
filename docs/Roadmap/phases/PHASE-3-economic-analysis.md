---
project: Casa Segura
doc_type: phase_index
phase: 3
status: living
last_updated: 2026-05-16
tags:
  - casa-segura
  - roadmap
  - phase-3
---

# Phase 3 - Economic Analysis

Goal: compute derived economic figures, compare them against source-cited benchmarks, and emit an `EconomicSummary` for category B rubric evaluators and reports.

Source epic:

- [EPIC-05 - Economic Analysis & Benchmarks](../EPIC-05-economic-analysis.md)

Source-of-truth links:

- [PRD_F5_ANALISIS_ECONOMICO](../../Casa%20Segura%20Formal%20PRDs/PRD_F5_ANALISIS_ECONOMICO.md) - economic calculations and benchmark expectations.
- [RUBRICA_CONTRATO](../../Casa%20Segura%20Formal%20PRDs/RUBRICA_CONTRATO.md) - numeric thresholds consumed by category B evaluators.
- [DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md) - `EconomicBenchmark` and economic summary persistence shape.
- [F5 analysis plan](../../analysis/F5_analisis_economico/IMPLEMENTATION_PLAN.md) - implementation breakdown.
- [F5 evaluation coverage](../../analysis/F5_analisis_economico/EVALUATION_COVERAGE.md) - boundary-value coverage expectations.

## Ready Now

- **CS-131** — Effective annual rate normalization. Inputs (`AggregatedExtraction.slots`) and benchmarks (`BenchmarkVersion 2026-Q2`) are both wired; pick up `backend/economics/application/rate_normalizer.py`.

**CS-130 closed 2026-05-16.** 18-row catalog at `backend/fixtures/economic_benchmarks_2026q2.yaml`; `manage.py seed_benchmark_version` + `manage.py load_benchmark_catalog --activate` boot the active benchmark version. `economics.application.version.latest_active()` exposes the singleton for downstream tickets.

## FE WORK

No primary FE tickets live in this phase. FE consumes these outputs later in report/result surfaces.

## BE WORK

- [CS-131](../tickets/CS-131.md) - Effective annual rate computation.
- [CS-132](../tickets/CS-132.md) - Monthly payment ratio computation.
- [CS-133](../tickets/CS-133.md) - Total cost computation.
- [CS-134](../tickets/CS-134.md) - Overcost vs benchmark in USD.
- [CS-135](../tickets/CS-135.md) - `EconomicSummary` Pydantic model.
- [CS-136](../tickets/CS-136.md) - Benchmark version stamp on summary.
- [CS-137](../tickets/CS-137.md) - Renormalization when fields are unverifiable.

## INFRA WORK

- [CS-130](../tickets/CS-130.md) — `economic_benchmarks.yaml` schema and initial values. **`done` (2026-05-16).**

Benchmark data is versioned (`BenchmarkVersion.version`), fixture-covered (`economic_benchmarks_2026q2.yaml`), and every row carries a `source` citation. Legal verification of the seed values remains an open follow-up (RUBRICA §17); rows currently carry `source_status: pending_verification` in `notes`.

## API / AI CONNECTIONS

No primary API / AI tickets live in this phase. The main integration point is the `EconomicSummary` contract consumed by Phase 4 rubric evaluators and Phase 5 reports.

## Parallel Pick Guidance

- BE owns computations, `EconomicSummary`, version stamping, and missing-field renormalization.
- INFRA WORK owns benchmark schema, fixture management, and source review.
- API / AI and rubric owners should review `EconomicSummary` before Phase 4 starts, because category B depends on these shapes.

