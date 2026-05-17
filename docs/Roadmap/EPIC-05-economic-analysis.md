---
id: EPIC-05
name: Economic Analysis & Benchmarks
phase: 3
status: in_progress
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

> **In progress.** CS-130 (`economic_benchmarks.yaml` + loader + seed) shipped 2026-05-16; the deterministic computation pipeline (CS-131..CS-137) lands ticket-by-ticket.

## Goal

Compute derived economic figures from extracted fields (effective annual rate, monthly payment, total cost, overcost vs benchmark), compare against `economic_benchmarks.yaml` per [[RUBRICA_CONTRATO]] §14, populate `EconomicSummary` consumed by category B evaluators and the report.

## Definition of done

- [x] `economic_benchmarks.yaml` lives in repo with source-cited values per [[RUBRICA_CONTRATO]] §14 _(CS-130 — 18-row seed at `backend/fixtures/economic_benchmarks_2026q2.yaml`; loader + management commands shipped; all rows still flagged `source_status: pending_verification` until legal sign-off)_
- [ ] Derived figures: effective annual rate (from any expressed form), monthly payment ratio, total cost multiplier, overcost in USD
- [ ] Comparison against benchmarks produces a tagged `EconomicSummary`
- [ ] Benchmark version stamped on every analysis ([[PRD_GENERAL]] BR-13)

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
