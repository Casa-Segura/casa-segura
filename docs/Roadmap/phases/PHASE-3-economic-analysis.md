---
project: Casa Segura
doc_type: phase_index
phase: 3
status: living
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - phase-3
---

# Phase 3 - Economic Analysis

Goal: compute derived economic figures, compare them against source-cited benchmarks, and emit an `EconomicSummary` for category B rubric evaluators and reports.

Source epic:

- [EPIC-05 - Economic Analysis & Benchmarks](../EPIC-05-economic-analysis.md)

## Tickets

- [CS-130](../tickets/CS-130.md) - `economic_benchmarks.yaml` schema and initial values.
- [CS-131](../tickets/CS-131.md) - Effective annual rate computation.
- [CS-132](../tickets/CS-132.md) - Monthly payment ratio computation.
- [CS-133](../tickets/CS-133.md) - Total cost computation.
- [CS-134](../tickets/CS-134.md) - Overcost vs benchmark in USD.
- [CS-135](../tickets/CS-135.md) - `EconomicSummary` Pydantic model.
- [CS-136](../tickets/CS-136.md) - Benchmark version stamp on summary.
- [CS-137](../tickets/CS-137.md) - Renormalization when fields are unverifiable.

## Parallel Pick Guidance

- Data/Backend owner: benchmark schema, computations, summary model, and version stamping.
- QA owner: boundary coverage for rates, payment ratios, missing fields, and asymmetric penalty inputs.
- Rubric owner should review outputs before Phase 4 starts, because category B depends on these shapes.

