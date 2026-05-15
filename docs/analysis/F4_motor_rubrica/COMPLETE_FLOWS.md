# Complete Flows — F4: Rubric Engine

> Generated: 2026-05-15

---

## Flow Index

| # | Flow Name | Type | Complexity |
|---|---|---|---|
| 1 | Standard evaluation (no override) | Worker | High |
| 2 | Evaluation with override (force score 0) | Worker | High |
| 3 | Economic-barrier wait (F4 ↔ F5) | Worker | Medium |
| 4 | Unverifiable propagation from F5 | Worker | Low |
| 5 | Finding emission without legal basis | Worker | Low |
| 6 | Internal QA: evaluate one criterion | DRF request | Low |
| 7 | Internal list criteria of a rubric version | DRF request | Low |
| 8 | F4 timeout → failed_analysis | Worker | Medium |

---

## Flow 1: Standard evaluation (no override)

### Pre-conditions

- `ContractAnalysis` row exists with `contract_type`, `project_id`, `elements_detected` set by F2.
- An active `RubricVersion` with its 38 `Criterion` rows seeded.
- F3 corpus active.
- F5 has set `economic_summary` (or the analysis type makes economic criteria N/A).

### Trigger

Redis stream `classification.to_rubric_and_economics` (consumer group `rubric`) receives a `ClassificationDone` envelope.

### Happy Path

**1. Daemon → Celery**
- Daemon `XREADGROUP`, calls `rubric.evaluate_analysis.delay(analysis_id)`, `XACK`.

**2. Task → Service**
- `RubricEvaluationService.evaluate(analysis_id)`.

**3. Load inputs**
- `ContractAnalysisRepository.load_full(analysis_id)` returns the row plus joined data.
- Determine `rubric_version`: prefer the one on the analysis row if set; else read the active version.

**4. Wait for F5**
- Poll `contract_analysis.economic_summary` with backoff (1, 2, 4, 8, 16, 32 s; total ≤ 60 s).
- If still missing and `contract_type` requires economic evaluation → proceed but mark economic criteria as unverifiable.

**5. Load criteria**
- `CriterionRepository.list_for_version(rubric_version, applicable_to_types=[contract_type])`. Returns ~32 rows for typical CVP.

**6. Evaluate criteria in parallel**
- `asyncio.gather(...)` bounded by `Semaphore(8)`.
- Per criterion:
  - Build prompt from `Criterion.evaluation_prompt` interpolating contract text, elements_detected, economic values.
  - POST OpenRouter `/chat/completions` with `temperature=0.1`, `response_format=json_object`, `Idempotency-Key=analysis:{analysis_id}:f4:crit:{criterion_id}`, timeout 30 s.
  - Parse with `JsonResponseParser`.
  - Validate against `RawEvaluation` Pydantic model.
  - If `unverifiable=true` → force `score = criterion.worst_case_when_unverifiable`.
  - Return `CriterionEvaluation`.

**7. Compute scores**
- For each category: `ScoreCalculator.compute_category_score(evals_in_category, criteria_in_category)`.
- `ScoreCalculator.compute_total(category_scores, global_weights, overrides=[])` returns `(score_total, band)`.
- Round to 1 decimal.

**8. Emit findings**
- `FindingFactory.emit_findings(evals, criteria, ctx)`:
  - Skip criteria with `score=10`.
  - Per remaining criterion: severity from score+override; build description from `justification`; attach `evidence_clause_snippet` (≤ 500 chars from `evidence_snippet`); call F3 for `legal_basis`.
  - Order: critical → red → yellow → green → unverifiable; within each, by `weight_in_category` desc.

**9. Executive summary**
- Last LLM call with the §8.3 prompt. Inputs: `contract_type`, `score_total`, `band`, `override_triggered`, finding counts per severity, `overcost_vs_benchmark_usd`.

**10. Persist**
- One UPDATE on `contract_analysis` writing:
  - `score_total`, `band`, `override_triggered`
  - `scores_by_category` (JSONB)
  - `criterion_evaluations` (JSONB)
  - `findings` (JSONB)
  - `findings_count`, `critical_findings_count`, `unverifiable_count`
  - `executive_summary`
  - `rubric_version`, `corpus_version`, `benchmark_version` (referenced versions)
  - `processing_completed_at = NOW()` (NB: the column is `contract_submission.processing_completed_at` — F4 also sets `contract_submission.processing_status = 'completed'` via `ContractSubmissionRepository.update_status`).

**11. Trigger F6 chain**
- `chain(reports_tasks.materialize_report.s(analysis_id), delivery_tasks.deliver_to_user.s()).apply_async()`.

### Error Scenarios

| ID | Condition | Outcome |
|---|---|---|
| E-1 | LLM 401 | failed_analysis, `error_code=LLM_AUTH_FAILED`, alert |
| E-2 | LLM transient on a single criterion | One retry; if again → mark that criterion unverifiable, continue overall flow |
| E-3 | LLM parse failure for a criterion | One retry; if again → unverifiable, continue |
| E-4 | Circuit breaker open mid-flow | New LLM calls fail-fast; criteria already in flight may complete; the rest become unverifiable; flow continues with degraded result |
| E-5 | Total elapsed > 60 s P95 budget | Continue but Prometheus alerts; not a kill condition unless 5 min absolute timeout |
| E-6 | F3 unreachable | Findings ship with empty `legal_basis` tagged `unverifiable_legal` (assuming the criterion has legal_anchor) |
| E-7 | Postgres unavailable during persist | Celery task auto-retries with backoff; idempotent on retry by `analysis_id` |

---

## Flow 2: Evaluation with override

### Trigger

At least one `CriterionEvaluation.override_triggered != None` collected during step 6.

### Happy Path

1. Same as Flow 1 up to step 7.
2. `ScoreCalculator.compute_total(category_scores, weights, overrides=["art_12_lpc"])` returns `(0.0, RED)`.
3. Per-category scores are still computed honestly (the report displays the breakdown).
4. `findings` for override-triggered criteria carry `severity=critical` and `anchors_to_override=<code>`.
5. The executive summary prompt receives `override_triggered=["art_12_lpc"]` and produces a sentence that mentions it.

---

## Flow 3: F4 ↔ F5 barrier wait

### Trigger

F4 starts evaluation; needs `economic_summary`.

### Happy Path

```mermaid
sequenceDiagram
    participant Svc as RubricEvaluationService
    participant AR as ContractAnalysisRepository
    participant F5 as F5 task (running in parallel)

    Svc->>AR: SELECT economic_summary FROM contract_analysis WHERE id=$1
    AR-->>Svc: null
    Svc->>Svc: sleep 1s
    F5->>AR: UPDATE contract_analysis SET economic_summary=... WHERE id=$1
    Svc->>AR: SELECT again
    AR-->>Svc: {price_cash: 80000, ...}
    Note over Svc: barrier released; proceed
```

If after 60 s the value is still null:
1. Log warning `f4_economic_barrier_timeout`.
2. Mark economic-dependent criteria (B1–B9, B5, etc.) as unverifiable.
3. Continue evaluation of non-economic criteria normally.
4. Persist with `economic_summary_warnings` noting the timeout.

---

## Flow 4: Unverifiable propagation from F5

### Trigger

F5's `EconomicSummary.warnings` includes a code like `annual_rate_not_expressed` or `interest_calculation_base_unfavorable`.

### Happy Path

1. F4 reads warnings during step 3.
2. For each criterion whose evaluation depends on the missing/invalid economic value (per BR-15 table), F4 skips the LLM call and emits:
   - `CriterionEvaluation(unverifiable=true, score=criterion.worst_case_when_unverifiable, justification="<value> not extractable from contract")`.
3. The corresponding finding is emitted with `severity=unverifiable`.

### Notes

The criterion-to-economic-value dependency table lives in `rubric/criteria/v1.0.0.yaml` per criterion (`depends_on_economic: ["annual_rate_pct"]`). F4 reads this when deciding to short-circuit.

---

## Flow 5: Finding without legal basis

(See `SOLUTION_DIAGRAMS.md` §2.4 and `DESIGN_PATTERNS.md` Cite-or-Stay-Silent.)

---

## Flow 6: Internal QA — evaluate one criterion

### Trigger

`POST /v1/internal/rubric/evaluate-criterion` with `X-Internal-Auth`.

### Happy Path

```json
{
    "criterion_id": "B2",
    "rubric_version": "1.0.0",
    "contract_text": "...full text...",
    "contract_type": "CVP",
    "economic_fields": {...},
    "elements_detected": {...}
}
```

The view calls `CriterionEvaluator.evaluate(criterion, ctx)` directly (no `analysis_id`, no persistence). Returns:

```json
{
    "score": 2.0,
    "unverifiable": false,
    "override_triggered": "art_12_lpc",
    "justification": "...",
    "evidence_snippet": "...",
    "tokens_consumed": 1820,
    "cost_estimate_cents": 5,
    "elapsed_ms": 4100
}
```

---

## Flow 7: Internal list criteria

`GET /v1/internal/rubric/version/{version}` with `X-Internal-Auth` → returns `[Criterion]` array (paginated if > 100 future-proofing).

---

## Flow 8: F4 total timeout → failed_analysis

### Trigger

Total wall time from task start exceeds 5 minutes (`F4_HARD_TIMEOUT_SECONDS`).

### Happy Path

1. Service catches `asyncio.TimeoutError` from the bounded gather.
2. Mark `contract_submission.processing_status = 'failed_analysis'`, `error_code=TIMEOUT_EXCEEDED`.
3. Do not persist partial `contract_analysis` evaluation columns.
4. Do not call F6.
5. Operator can manually retry via `POST /v1/internal/submissions/{id}/retry-rubric`.

---

**End of document.**
