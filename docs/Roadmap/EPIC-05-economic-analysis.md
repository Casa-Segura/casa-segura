---
id: EPIC-05
name: Economic Analysis & Benchmarks
phase: 3
status: done
depends_on:
  - EPIC-04
prd_refs:
  - PRD_GENERAL §1 (Art. 1686 CC motivation)
  - FEATURES_MAP §4 (F5)
  - RUBRICA_CONTRATO §5, §14
feature: F5
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-05
---

# EPIC-05 — Economic Analysis & Benchmarks

> **Done — 2026-05-16.** All 8 tickets (CS-130..CS-137) landed. The deterministic F5 pipeline produces `EconomicSummary` envelopes matching `docs/analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md`. No LLM calls anywhere in `backend/economics/` (PRD_F5 BR-13). Wiring from classification into `analyze()` is owned by CS-112 (EPIC-04 orchestrator).

## Goal

Compute derived economic figures from extracted fields (effective annual rate, monthly payment, total cost, overcost vs benchmark), compare against `economic_benchmarks.yaml` per [[RUBRICA_CONTRATO]] §14, populate `EconomicSummary` consumed by category B evaluators and the report.

## Definition of done

- [x] `economic_benchmarks.yaml` lives in repo with source-cited values per [[RUBRICA_CONTRATO]] §14 _(CS-130 — 21-row seed at `backend/fixtures/economic_benchmarks_2026q2.yaml`; loader + management commands shipped; all rows still flagged `source_status: pending_verification` until legal sign-off)_
- [x] Derived figures: effective annual rate (from any expressed form), monthly payment ratio, total cost multiplier, overcost in USD _(CS-131 rate normalizer with compound BR-05 conversion; CS-132 `MonthlyRatioBand` classifier; CS-133 `TotalCostBundle` with French amort + BR-07 coherence; CS-134 overcost re-amortization with BR-02 / BR-11 asymmetric guards)_
- [x] Comparison against benchmarks produces a tagged `EconomicSummary` _(CS-135 `analyze()` assembler emits the envelope shape from `ECONOMIC_SUMMARY_CONTRACT.md` with `derivation_status`, deduped `warnings`, and `benchmark_comparisons`)_
- [x] Benchmark version stamped on every analysis ([[PRD_GENERAL]] BR-13) _(CS-136 — byte-equal echo between active `BenchmarkVersion.version` and `summary.benchmark_version`; structlog default-versions processor now also injects `benchmark_version`; BR-12 non-blocking stale signal via `assert_freshness`)_
- [x] Insufficient-data path remains schema-valid without zero substitution _(CS-137 — `_derive_status` returns `INSUFFICIENT_DATA` when nothing usable came through; renormalizer cross-slot precursors `down_payment_inconsistent` + `total_cost_not_disclosed`; BR-09 honesty guard pinned by Rule 9 test)_

## Tickets (titles only — stubs)

- [[CS-130]] — `economic_benchmarks.yaml` schema and initial values
- [[CS-131]] — Effective annual rate computation from monthly / nominal forms
- [[CS-132]] — Monthly payment ratio computation
- [[CS-133]] — Total cost computation
- [[CS-134]] — Overcost vs benchmark in USD
- [[CS-135]] — `EconomicSummary` pydantic model
- [[CS-136]] — Benchmark version stamp on summary
- [[CS-137]] — Renormalization when fields are unverifiable

## Notes

- [[RUBRICA_CONTRATO]] §14 has the full benchmark schema and the source attribution policy
- Asymmetric penalty rule applies here: better-than-benchmark inputs do not penalize
