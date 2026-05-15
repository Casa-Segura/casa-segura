# Feature Overview — F5: Economic Analysis & Benchmarks

> Generated: 2026-05-15
> Stack: Django 5.2 LTS + Celery + Postgres (no LLM in F5)

---

## Executive Summary

F2 extracts raw economic fields from the contract. F5 turns them into the persisted `EconomicSummary`: validated, normalized, derived, and compared against versioned market benchmarks. The output drives F4's economic criteria and F6's economic-analysis section of the report.

F5 is **fully deterministic** — no LLM, no randomness. The same inputs produce the same outputs. This is critical because economic figures are the user's most concrete decision input ("you'd pay $X more than the market"), and the product cannot afford volatility there. Reproducibility is also why benchmarks are versioned in `BenchmarkVersion`: an analysis recorded under `benchmark_version='2026-Q2'` remains explainable in `2027-Q1`.

Behavior is asymmetric: a contract value better than the benchmark never penalizes. A 5% down payment when the standard is 10% is favorable, not suspicious. F5 records the assessment (`below_market_favorable`, `within_market`, `above_market`, `well_above_market`) and lets F4 apply the rubric's asymmetric scale.

---

## Key Concepts

| Term | Plain-language definition |
|---|---|
| **EconomicFieldsRaw** | What F2 hands F5: each field with `value`, `confidence`, `evidence_snippet` |
| **EconomicSummary** | What F5 produces: validated fields + derived computations + benchmark comparisons + overcost + warnings |
| **BenchmarkComparison** | Per-metric `contract_value`, `benchmark_value`, `delta`, `assessment` |
| **Overcost** | Difference in total cost between the contract and a benchmark-substituted scenario |
| **BenchmarkVersion** | Versioned snapshot of `economic_benchmarks.yaml` |
| **Asymmetric penalty** | Favorable values produce `below_market_favorable`, never a penalty |
| **Coherence cross-check** | Detect monthly payment that doesn't match the declared rate (suggests hidden costs) |

---

## How It Works (Step by Step)

1. **F5 consumes** `ClassificationDone` from the same stream as F4 (different consumer group `economics`).
2. **Skip if not applicable**: if `contract_type` not in `{CVP, APV, LEA, FSV, ARV}`, F5 produces a minimal summary (only `price_cash` if present) and exits early. For CVC and most ARC, the economic computation is degenerate.
3. **Normalize fields**: convert currencies (SVC→USD at fixed 8.75 parity), percentages (always decimal), terms (always months), rates (compute annual when only monthly given).
4. **Validate ranges**: reject values out of plausible bounds (e.g., `annual_rate_pct > 1.0`).
5. **Derive fields**: `financed_amount = price - down`; `total_cost_paid = down + monthly_payment * term_months`; theoretical monthly payment via French amortization formula.
6. **Coherence cross-check**: if extracted `monthly_payment` differs by > 5% from the theoretical, emit a `coherence_warning`.
7. **Load benchmarks** for the active `BenchmarkVersion`, filtered by `applicable_contract_types`.
8. **Build BenchmarkComparison** per metric: down payment, annual rate, term, total-cost multiplier, monthly payment.
9. **Compute overcost**: theoretical total cost at benchmark (rate substituted, others kept) vs. contract total cost.
10. **Emit warnings**: codes like `interest_calculation_base_unfavorable`, `total_cost_not_disclosed`, `term_excessive`.
11. **Persist** `economic_summary` (JSONB) and `benchmark_version` on `contract_analysis`. This **unblocks F4**'s watermark wait.

---

## Business Rules

- **BR-F5-01:** Benchmarks are versioned; each analysis pins its `benchmark_version`.
- **BR-F5-02:** Asymmetric penalty: favorable never penalizes.
- **BR-F5-03:** Conservative on ambiguity: take the worst case for the buyer.
- **BR-F5-04:** SVC→USD fixed 8.75 parity.
- **BR-F5-05:** Monthly→annual rate via compound formula `(1+m)^12 − 1`.
- **BR-F5-06:** French amortization standard.
- **BR-F5-07:** Coherence tolerance 5%.
- **BR-F5-08:** Warnings are hints; F4 decides if they become findings.
- **BR-F5-09:** Insufficient data → write `economic_summary` with `derivation_status='insufficient_data'` and empty fields; F4 marks economic criteria unverifiable.
- **BR-F5-10:** Overcost computed against the **applicable segment benchmark**, not the cheapest possible (so a developer-direct CVP compares against the developer-direct range, not the bank range).
- **BR-F5-11:** For FSV contracts within the published FSV range, no overcost vs. bank range; only vs. FSV.
- **BR-F5-12:** Expired benchmarks (`next_review_due < today`) emit ops alert but do not block.
- **BR-F5-13:** F5 makes zero LLM calls.
- **BR-F5-14:** Currency assumed USD unless contract declares SVC.

---

## Lifecycle Diagram

Stateless per analysis. The state of F5 within one analysis: `start → normalized → derived → compared → persisted`.

---

## What Changes in the System

- New persistent catalog tables: `benchmark_version`, `economic_benchmark` (declared by F8).
- New `economic_benchmarks.yaml` file under `economics/benchmarks/`.
- New management commands: `benchmarks_load --version 2026-Q2`, `benchmarks_activate --version 2026-Q2`.
- Columns written on `contract_analysis`: `economic_summary` (JSONB), `benchmark_version` (FK).
- Celery task: `economics.compute_summary`.
- Internal endpoints: `POST /v1/internal/economic/analyze`, `GET /v1/internal/economic/benchmarks`.

---

## What This Feature Does NOT Do

- Extract economic fields (F2)
- Persist by itself any score or finding (F4)
- Personalize by user income (not in scope)
- Compute future rates or projections
- Compute taxes or notary costs separately

---

## Audit and Compliance

- Each computation logged: `analysis_id`, `benchmark_version`, list of warning codes, derivation_status, elapsed_ms.
- No PII; only aggregate figures.
- Persisted `economic_summary` is anonymized at 90 days to bucket ranges (F8).

---

## Assumptions Made

- Default benchmark version `2026-Q2` (loaded at bootstrap).
- Quarterly benchmark review.
- USD assumed; SVC→USD via fixed parity 8.75.
- French amortization standard (PRD §10 Q-4 deferral of graduated installments).

---

**End of document.**
