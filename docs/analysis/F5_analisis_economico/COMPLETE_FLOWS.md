# Complete Flows — F5: Economic Analysis & Benchmarks

> Generated: 2026-05-15

---

## Flow Index

| # | Flow Name |
|---|---|
| 1 | Compute summary — full data |
| 2 | Compute summary — insufficient data |
| 3 | Load benchmarks (operator) |
| 4 | Activate benchmarks |
| 5 | Internal QA: analyze raw fields |
| 6 | List active benchmarks (operator) |

---

## Flow 1: Compute summary — full data

### Pre-conditions
- ContractAnalysis exists; F2 has set `contract_type` and committed.
- Active `BenchmarkVersion` exists.

### Trigger
Redis stream `classification.to_rubric_and_economics` (consumer group `economics`) entry.

### Happy Path

1. **Consumer** XREADGROUP, decode envelope.
2. **Dispatch** `economics.compute_summary.delay(analysis_id, raw_fields_json, contract_type)`.
3. **Task** loads benchmarks for active version + applicable_to_types.
4. **Service** normalizes raw fields (currency, %, term, rates).
5. **Service** computes derived (financed_amount, total_cost_paid, multiplier, theoretical monthly).
6. **Service** coherence cross-check 5%; emit warning if needed.
7. **Service** builds `BenchmarkComparison` per metric.
8. **Service** computes overcost (substituted-rate amortization).
9. **Service** emits warning codes.
10. **Service** persists `economic_summary` + `benchmark_version` on `contract_analysis`.
11. **XACK** the stream.

### Post-conditions
- `contract_analysis.economic_summary` populated
- F4 barrier wait releases on next poll

---

## Flow 2: Compute summary — insufficient data

### Trigger
Raw fields all `null` (typical CVC cash or contracts where F2 couldn't extract anything).

### Happy Path

1. Same as Flow 1 up to step 4.
2. Service detects `ExtractedFields` all-empty.
3. Build `EconomicSummary(derivation_status="insufficient_data", fields_extracted=empty, warnings=[])`.
4. Persist as Flow 1 step 10.

### Notes

F4 will see `economic_summary IS NOT NULL` and proceed; economic criteria evaluate as unverifiable (BR-15) via `Criterion.depends_on_economic` short-circuit.

---

## Flow 3: Load benchmarks (operator)

### Trigger
`python manage.py benchmarks_load --version 2026-Q2 --path economics/benchmarks/2026-Q2.yaml`

### Happy Path

1. Parse YAML via `BenchmarkLoader.load_yaml(path)`.
2. Validate: all required fields present per row; dates well-formed; `unit` in enum; numeric ranges sane.
3. Check `BenchmarkVersion` not already in DB (or `--force`).
4. Transaction:
   - bulk_create `EconomicBenchmark` rows
   - create `BenchmarkVersion(is_active=False)`
5. Print summary (rows created).
6. Audit log entry.

### Errors

- Missing required field → ParseError + rollback
- Duplicate `benchmark_key` in YAML → ValidationError + rollback
- Date next_review_due before last_updated → ValidationError

---

## Flow 4: Activate benchmarks

### Trigger
`python manage.py benchmarks_activate --version 2026-Q2`

### Happy Path
1. Transaction:
   - UPDATE all `is_active=true` rows to `is_active=false`
   - UPDATE the target row to `is_active=true`
2. Audit log.

The partial unique index guarantees no two active versions.

---

## Flow 5: Internal QA — analyze raw fields

### Trigger
`POST /v1/internal/economic/analyze` with `X-Internal-Auth`.

### Request

```json
{
    "contract_type": "CVP",
    "economic_fields_raw": {
        "price_cash": {"value": 80000, "currency": "USD", "confidence": 0.95, "evidence_snippet": "..."},
        "annual_rate_pct": {"value": 0.18, "confidence": 0.85, "evidence_snippet": "..."},
        "term_months": {"value": 240, "confidence": 0.9, "evidence_snippet": "..."},
        "down_payment_pct": {"value": 0.10, "confidence": 0.99, "evidence_snippet": "..."},
        "monthly_payment": {"value": 1083.50, "confidence": 0.91, "evidence_snippet": "..."}
    }
}
```

### Response

```json
{
    "economic_summary": { ... full structure ... },
    "warnings": [ ... ],
    "benchmark_version_used": "2026-Q2",
    "elapsed_ms": 12
}
```

Does **not** persist anything.

---

## Flow 6: List active benchmarks

`GET /v1/internal/economic/benchmarks?version=latest_active` returns the active benchmark catalog. Useful for operators verifying what the system is comparing against.

---

**End of document.**
