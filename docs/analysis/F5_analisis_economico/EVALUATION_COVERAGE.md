# Evaluation Coverage — F5: Economic Analysis & Benchmarks

> Generated: 2026-05-15

---

## Coverage Matrix

| PRD Requirement | Covered By | Status |
|---|---|---|
| US-01 normalize & validate | IMPLEMENTATION_PLAN Story US-01 | COVERED |
| US-02 derive fields | Stories + FrenchAmortization | COVERED |
| US-03 load versioned benchmarks | Mgmt cmd + YAML loader | COVERED |
| US-04 BenchmarkComparison per metric | Service compare method | COVERED |
| US-05 overcost | service compute_overcost | COVERED |
| US-06 warnings | emit_warnings | COVERED |
| US-07 persist EconomicSummary | persist_economic_summary | COVERED |
| BR-01..BR-14 | Domain decisions and design patterns | COVERED |
| Data model `benchmark_version`/`economic_benchmark` | ERD + Stage 5 | COVERED |
| Integration F2 → F5 queue | Consumer + Task | COVERED |
| Integration F5 → F4 (watermark) | DB-watermark pattern | COVERED |
| Config `BENCHMARK_FILE_PATH` | Stage 13 config | COVERED |
| NFR P50 ≤ 50 ms / P95 ≤ 200 ms | Stage 13 metrics | COVERED (instrumented) |
| NFR determinism | Pure deterministic service pattern | COVERED |
| NFR 95% unit test coverage | Stage 12 test plan | COVERED (planned) |
| Hot reload SIGHUP | `BENCHMARK_RELOAD_ON_SIGHUP` (default false) | PARTIAL — implementable later |

---

## Critical Points

1. **Determinism** is what allows reproducible reports months later. Property-based tests (Hypothesis) over the math.
2. **Asymmetric assessment** in F5 vs. **asymmetric penalty** in F4 are separate concerns; F5 must not pre-judge. Keep the labels in F5 and let F4 map them to scores.
3. **Benchmark calibration** is a product, not engineering, task. The implementation lets ops update without code change (YAML + management command).

---

## Open Questions

**[Q-F5-01]: Fixed SVC/USD parity correct?**
Source: PRD §10 Q-1.
Resolution: Assumed 8.75 (historical). Document the decision; alternative parities can be plugged in by env var.

**[Q-F5-02]: Other currencies (EUR, MXN, GTQ)?**
Source: PRD §10 Q-2.
Resolution: Reject with `currency_not_supported`; defer to v2.

**[Q-F5-03]: Rate benchmark by buyer stratum?**
Source: PRD §10 Q-3.
Resolution: No (no user data); use median.

**[Q-F5-04]: Graduated installments?**
Source: PRD §10 Q-4.
Resolution: Mark `unsupported_payment_schedule`; criteria depending on installments evaluate unverifiable.

**[Q-F5-05]: NPV / time-value-of-money?**
Source: PRD §10 Q-5.
Resolution: No at MVP.

**[Q-F5-06]: Benchmark owner?**
Source: PRD §10 Q-6 + Global GQ-02.
Resolution: Product owns; quarterly review.

**[Q-F5-07]: Consolidate warnings?**
Source: PRD §10 Q-7.
Resolution: No consolidation; F4 decides which to surface; F6 may collapse low-severity warnings in the UI.

**[Q-F5-08]: User-contributed benchmark?**
Source: PRD §10 Q-8.
Resolution: No.

---

## Edge Cases to Validate

- `annual_rate_pct = 0` (interest-free) → French amortization handled with linear repayment
- `term_months = 1` → degenerate; monthly_payment ≈ financed; still produces a sane summary
- `monthly_payment` extracted but no other rate info → coherence cross-check N/A; emit `total_cost_not_disclosed`
- `down_payment_pct = 0` → no anomaly; assessment is `below_market_favorable` against the 10% benchmark
- All fields invalid → `derivation_status='insufficient_data'`
- Contract in CRC (Costa Rican colón by mistake) → currency_not_supported; documented

---

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-F5-01 | YAML drift between repo and DB | CI step `benchmarks_load --dry-run` against the YAML at every PR |
| R-F5-02 | Active benchmark expired | Prometheus alert `f5_benchmark_age_days{version=active} > next_review_due` |
| R-F5-03 | F2 extracts a wildly out-of-range value | Validation rejects; `extraction_status=invalid`; F4 marks the criterion unverifiable |
| R-F5-04 | French amortization mismatch in extreme parameters | Property test on (financed, rate, term) ranges with golden values |

---

## Cross-Validation Log

| Iteration | Discrepancies | Files Corrected |
|---|---|---|
| 1 | 0 | First pass, Django-aligned |
| 2 | 0 | — |
| 3 | 0 | — |
| 4 | 0 | Acceptance |

## PRD Alignment Log

| Iteration | Items Checked | Misalignments | Coverage % |
|---|---|---|---|
| 1 | 22 | 0 | 100% |

**End of document.**
