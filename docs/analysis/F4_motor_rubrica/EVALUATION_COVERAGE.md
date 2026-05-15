# Evaluation Coverage — F4: Rubric Engine

> Generated: 2026-05-15

---

## PRD Contradictions

None within PRD_F4. Cross-PRD items handled in `_shared/GLOBAL_ASSUMPTIONS.md`.

---

## Coverage Matrix

| PRD Requirement | Covered By | Status |
|---|---|---|
| US-01 evaluate criteria | IMPLEMENTATION_PLAN Story US-01 + Stage 4 service | COVERED |
| US-02 override detection | SOLUTION_DIAGRAMS §2.2 + Story US-02 | COVERED |
| US-03 anchor via F3 | FindingFactory + Story US-03 | COVERED |
| US-04 category scores with renormalization | ScoreCalculator + Story US-04 | COVERED |
| US-05 total score | ScoreCalculator + Story US-05 | COVERED |
| US-06 severity-prioritized findings | Story US-06 ordering | COVERED |
| US-07 persist | Story US-07 atomic UPDATE | COVERED |
| US-08 executive summary | Story US-08 + LLM prompt | COVERED |
| BR-01..BR-16 | Mapped across DESIGN_PATTERNS + COMPLETE_FLOWS + IMPLEMENTATION_PLAN | COVERED |
| Data: Criterion catalog | ERD + Stage 5 model + Stage 6 seed | COVERED |
| Data: RubricVersion catalog | ERD + Stage 5 | COVERED |
| Updates to `contract_analysis` | IMPLEMENTATION_PLAN Story US-07 | COVERED |
| Integration: F2 → F4 queue | Consumer + Task | COVERED |
| Integration: F4 ↔ F5 watermark | COMPLETE_FLOWS Flow 3 | COVERED |
| Integration: F4 → F6 chain | RubricEvaluationService persist + chain dispatch | COVERED |
| LLM Prompts §8.1 / §8.2 / §8.3 | Stage 8 prompts.py verbatim | COVERED |
| 11 Overrides table | OverrideCode TextChoices + criteria YAML mapping | COVERED |
| NFR P50 ≤ 40 s | Stage 13 metrics | COVERED (instrumented) |
| NFR P95 ≤ 60 s | Stage 13 metrics + hard timeout | COVERED |
| NFR reproducibility ±0.2 | Temp 0.1 + seed when supported | COVERED |
| NFR cost ≤ $0.30 USD | Metrics + concurrency cap | COVERED (instrumented) |
| NFR ≥ 70% findings with citation | Tracked via `f4_legal_basis_empty_total` | COVERED (instrumented) |

---

## Critical Points

1. **Override correctness** — A missed override (especially `art_12_lpc` on hidden total-balance interest) is the largest product harm. The override binding lives in the criterion YAML and the seed migration; QA must label real contracts where overrides apply and assert F4 fires them.
2. **Cost ceiling** — 32 criteria × $0.005 = $0.16 + 1 summary call ≈ $0.20. Within $0.30 budget. Concurrency cap protects against rate limits.
3. **Unverifiable propagation** — F5 warnings must reach F4 in time; the watermark barrier and the `depends_on_economic` shortcut both protect against false positives.
4. **Score determinism** — Same `(submission_hash, rubric_version, corpus_version, benchmark_version)` should produce the same score within ±0.2. Test this with a fixed test contract through CI.
5. **Findings cap in UI vs. all findings persisted** — F4 persists all; F6 may visually cap. The PRD §10 Q-3 (cap at 25 findings) is a F6 concern.

---

## Open Questions

**[Q-F4-01]: Temperature 0.0 vs 0.1?**
Source: PRD §10 Q-1.
Resolution: 0.1 (current). 0.0 can produce degenerate outputs on some models. Reconsider if reproducibility variance exceeds ±0.2 in QA.

**[Q-F4-02]: Seed override?**
Source: PRD §10 Q-2.
Resolution: Optional via `LLM_RUBRIC_SEED` env var; only used in QA. Not all OpenRouter providers honor seed.

**[Q-F4-03]: Max findings shown in report?**
Source: PRD §10 Q-3.
Resolution: F4 persists all; F6 caps at 25 with rest collapsed under "Other observations". Surfaced in F6.

**[Q-F4-04]: F5 barrier — parallel or sequential?**
Source: PRD §10 Q-4.
Resolution: Parallel with DB watermark. F4 evaluates non-economic criteria immediately; economic criteria wait on F5 (or short-circuit to unverifiable).

**[Q-F4-05]: Show unverifiable findings to user?**
Source: PRD §10 Q-5.
Resolution: Yes (transparency). F6 renders them at the bottom of the findings list.

**[Q-F4-06]: How is corpus paraphrase fidelity validated?**
Source: PRD §10 Q-6.
Resolution: PR review process in F3; not F4's responsibility.

**[Q-F4-07]: Learn from previous evaluations?**
Source: PRD §10 Q-7.
Resolution: No at MVP. Each analysis is independent.

**[Q-F4-08]: Criterion with repealed legal anchor?**
Source: PRD §10 Q-8.
Resolution: F3's retrieval skips chunks where the parent `LegalDocument.status='repealed'` (filter added in repository). F4 receives no anchor; tag `unverifiable_legal`.

---

## Edge Cases to Validate

- All 6 categories have zero applicable criteria (impossible in practice but defensively handled) → band `not_analyzable`, score 0
- Override fires on a criterion with `score=10` (LLM bug) → score still forced to 0
- Two overrides on same criterion (e.g., A3 + A6) → both listed in `override_triggered`
- Three criteria depend on `annual_rate_pct`, F5 marks it `not_present` → all three short-circuit to unverifiable without LLM
- LLM returns score 10 for a criterion where the LLM thinks it's perfect, but `override_triggered` also set → score 0 (override wins)
- Per-criterion LLM call returns 25 s response time → close to 30 s timeout; semaphore protects parallelism
- Total wall time hits 5 min → fail clean; user told to retry

---

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-F4-01 | LLM drift on model upgrade changes criterion scores | Pin model; regression test set |
| R-F4-02 | Criterion YAML out of sync with active rubric_version | Seed migration enforces (version, id) UNIQUE; CI compares YAML hash to DB |
| R-F4-03 | F5 barrier hangs | 60 s timeout + degradation to unverifiable |
| R-F4-04 | OpenRouter rate-limit storms | Semaphore + circuit breaker |
| R-F4-05 | Findings persist failure leaves a half-evaluated analysis | UPDATE is atomic; if it fails, Celery retries; ContractSubmission status unchanged until UPDATE succeeds |

---

## Cross-Validation Log

| Iteration | Discrepancies Found | Files Corrected |
|---|---|---|
| 1 | 0 | Aligned with Django from start |
| 2 | 0 | Field names, command names, queue/stream names consistent |
| 3 | 0 | Endpoint paths consistent |
| 4 | 0 | Acceptance |

## PRD Alignment Log

| Iteration | PRD Items Checked | Misalignments | Coverage % |
|---|---|---|---|
| 1 | 32 | 0 | 100% |

---

**End of document.**
