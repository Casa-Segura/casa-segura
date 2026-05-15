# PRD: F5 — Economic Analysis & Benchmarks

**Version:** 1.0
**Status:** Approved for development
**Author:** Product Team
**Date:** 2026-05-10
**Depends on:** F2 (Classification + extracted economic fields), F8 (database schema base)
**Blocks:** F4 (Rubric Engine for economic criteria), F6 (Report Generation)

---

## 1. Problem Statement

The core value of Casa Segura for an ordinary person is to answer, in concrete numbers, whether the economic conditions of the contract suit them. The user does not need finance theory; they need to see "this contract will cost you $X more than the market average, over this term, at this rate". F5 is the layer that turns the economic fields F2 extracts into derived computations, compares them against configurable benchmarks, and produces an `EconomicSummary` consumable by F4 and F6.

The criticality of this layer comes from three facts. First, Art. 1686 of the Salvadoran Civil Code eliminates rescission for gross disparity ("lesión enorme"): the buyer cannot challenge an excessive price after signing. That makes ex-ante economic analysis the largest protection the system can offer. Second, market benchmarks are live parameters: the Central Bank rates change, the market average moves. F5 must consult versioned, citable benchmarks. Third, honesty is structural: if a value cannot be extracted from the contract, F5 does not invent or assume it; it marks it missing and leaves F4 to treat it as unverifiable.

The feature must be deterministic (same inputs = same outputs), traceable (every figure in the report must be traceable to a contract clause or a benchmark with cited source), and conservative (computations assume the reasonable worst case when there is ambiguity to avoid giving the user false comfort).

---

## 2. Scope

**In scope:**

- Validation and normalization of economic fields extracted by F2
- Unit conversions: fractional percentage/percentage point, monthly rate to effective annual, local currency to USD
- Computation of derived fields:
  - Financed amount (total price − down payment)
  - Total cost paid (sum of installments + additional costs)
  - Total cost vs. cash multiplier
  - Effective annual rate when only monthly rate is given
  - Cross-check of monthly payment vs. theoretical amortization
- Loading of the `economic_benchmarks.yaml` file with versioning
- Comparison of each contract figure against the applicable benchmark
- Computation of overcost in contract local currency vs. the "same conditions at benchmark" case
- Generation of `BenchmarkComparison` for each relevant metric
- Production of the complete `EconomicSummary` persisted in `ContractAnalysis.economic_summary`
- Detection of internal inconsistencies (e.g. monthly payment does not match the principal amortization at the declared rate)
- Detection of figures missing from the contract that should be present

**Out of scope:**

- Extracting the economic fields from the contract (that is F2)
- Applying score penalties for economic deviations (that is F4)
- Predicting rates or future market behavior
- Making recommendations on what rate to demand (that is F4 via finding recommendation)
- Personalized financial advice
- Comparison against specific products of named banks
- Computation of taxes or notary costs (these are part of total cost if in the contract, but not computed separately)
- User's ability to pay (the system never asks for the user's income)

---

## 3. User Stories

### US-01: System normalizes and validates extracted economic fields

**As the** system,
**I want to** validate the economic fields F2 extracted from the contract and normalize them to a canonical representation,
**So that** downstream computations work with consistent data.

**Acceptance criteria:**

- F5 receives the `economic_fields_raw` object from F2 with each field marked with `value`, `confidence`, `evidence_snippet`
- For each field:
  - If `value` is `null` or `confidence < 0.5`, the field is marked `not_present`
  - If `value` is not a valid number or is out of reasonable range, it is marked `invalid` with reason
  - If it passes validation, it is normalized to the canonical representation
- Canonical normalizations:
  - Currency: everything to USD (fixed historical factor ¢8.75/USD if the contract declares colones)
  - Percentages: decimal representation (0.10 for 10%, not 10 or "10%")
  - Terms: representation in months (years multiplied by 12, days divided by 30 with note)
  - Installments: absolute amount in USD per period of `payment_periodicity`
  - Rates: effective annual representation (`annual_rate_pct`), with `monthly_rate_pct` preserved if it came that way
- Range validations:
  - `price_cash`: > 0, < 5,000,000
  - `down_payment_pct`: ≥ 0, ≤ 1
  - `term_months`: > 0, ≤ 360 (30 years)
  - `annual_rate_pct`: ≥ 0, ≤ 1 (contracts almost never exceed 100% APR; if they do, it is almost certainly an extraction error)
  - `monthly_payment`: > 0, < 50,000
- If a validation fails, the field is marked `invalid` and the reason is noted; the computation continues with valid fields

### US-02: System computes derived fields

**As the** system,
**I want to** compute derived values from the extracted fields,
**So that** the `EconomicSummary` has comparable metrics.

**Acceptance criteria:**

- If `price_cash` and `down_payment` are present:
  - `financed_amount = price_cash - down_payment`
- If `price_cash` is present and `down_payment_pct` too:
  - Cross-check: `down_payment_inferred = price_cash * down_payment_pct` must match `down_payment` (5% tolerance)
  - If it does not match, an inconsistency is noted and the direct `down_payment` is used
- If `term_months`, `monthly_payment`, and `financed_amount` are present:
  - `total_cost_paid = down_payment + (monthly_payment × term_months)` (plus any identified one-time fee)
  - `total_cost_vs_cash_multiplier = total_cost_paid / price_cash`
- If only a monthly rate is given:
  - `annual_rate_pct = (1 + monthly_rate_pct)^12 - 1`
  - A `derivation_note: "converted from monthly rate"` is recorded
- If `annual_rate_pct`, `term_months`, and `financed_amount` are present but `monthly_payment` is missing:
  - The theoretical installment is computed with the French amortization formula
  - It is reported as `monthly_payment_theoretical` for comparison
- Coherence cross-check:
  - If `monthly_payment` is extracted but differs by more than 5% from the theoretical installment derived from `(financed_amount, annual_rate_pct, term_months)`, a `coherence_warning` is noted
  - This suggests the contract has hidden costs (the payment is higher than the declared rate justifies)
- If there is insufficient data to compute, derived fields remain `null`

**French amortization formula:**

```
monthly_payment = financed_amount * (r * (1+r)^n) / ((1+r)^n - 1)
where r = annual_rate_pct / 12
      n = term_months
```

### US-03: System loads versioned benchmarks

**As the** system,
**I want to** load economic benchmarks from a versioned configuration with cited source,
**So that** each analysis uses reproducible and auditable values.

**Acceptance criteria:**

- The `economic_benchmarks.yaml` file is loaded at service startup
- The file is versioned by semantic tag (e.g. `2026-Q2`) and every change requires explicit PR with cited source
- For each benchmark the required fields are: `value` (or `value_min`/`value_max`), `unit`, `source`, `source_url`, `last_updated`, `next_review_due`
- The current version is persisted as `EconomicBenchmark.benchmark_version` and referenced in each analysis
- If the file is malformed at load, the service fails at startup with a clear error
- Metrics are exposed: active version, age of each benchmark, expired benchmarks (next_review_due < today)
- An operational alert is emitted when there are expired benchmarks

**Required benchmarks (minimum list):**

| Key | Applies to | Unit | Expected source |
|---|---|---|---|
| `standard_down_payment_bank_purchase` | CVP, FSV | pct | Banking practice, ABANSA |
| `down_payment_range_direct_purchase` | CVP, APV | pct | Market observation |
| `bank_mortgage_rate_min` | CVP, FSV | annual pct | BCR |
| `bank_mortgage_rate_max` | CVP, FSV | annual pct | BCR |
| `bank_mortgage_rate_mid` | CVP, FSV | annual pct | BCR (computed) |
| `fsv_rate_min` | FSV | annual pct | FSV |
| `fsv_rate_max` | FSV | annual pct | FSV |
| `developer_direct_rate_min` | CVP, APV, LEA | annual pct | Market |
| `developer_direct_rate_max` | CVP, APV, LEA | annual pct | Market |
| `credit_term_max_reasonable` | CVP, APV, LEA, FSV | months | Practice |
| `credit_term_ivu_max` | IVU | months | Art. 2 Ley IVU |
| `cost_multiplier_healthy_max` | CVP, APV, LEA, FSV | ratio | Computation |
| `cost_multiplier_high_max` | CVP, APV, LEA, FSV | ratio | Computation |
| `cost_multiplier_excessive_min` | CVP, APV, LEA, FSV | ratio | Computation |

### US-04: System compares contract figures against benchmarks

**As the** system,
**I want to** produce a `BenchmarkComparison` object for each relevant metric,
**So that** F4 can apply criteria and F6 can show visual comparisons.

**Acceptance criteria:**

- For each available metric (down payment, annual rate, term, cost multiplier, monthly payment), F5 generates a `BenchmarkComparison`
- Each comparison contains: metric, contract value, benchmark value, absolute delta, percentage delta, assessment
- Possible assessments: `within_market`, `slightly_above_market`, `above_market`, `well_above_market`, `below_market_favorable`
- The assessment rule is asymmetric:
  - Rate, down payment, term, cost multiplier: penalize when exceeding the benchmark
  - If the contract value is less than the benchmark, it evaluates as `below_market_favorable` (no penalty)
- If the contract metric is `null`, no comparison is generated; F4 will see it as missing
- If the applicable benchmark does not exist (e.g. contract type without a rate benchmark), no comparison is generated

**Evaluation rule for rates (example, replicable for other metrics):**

```
delta_pct_points = (contract_value - benchmark_value) × 100

If delta_pct_points < 0:                     "below_market_favorable"
If 0 ≤ delta_pct_points < 1:                 "within_market"
If 1 ≤ delta_pct_points < 2:                 "slightly_above_market"
If 2 ≤ delta_pct_points < 5:                 "above_market"
If delta_pct_points ≥ 5:                     "well_above_market"
```

### US-05: System computes overcost against benchmark

**As the** system,
**I want to** compute how much more the buyer pays compared to the benchmark scenario,
**So that** the report shows a concrete figure in local currency.

**Acceptance criteria:**

- F5 computes the theoretical installment the contract would have if all unfavorable conditions were replaced with the benchmark
- The substitutions are:
  - If the annual rate is above `bank_mortgage_rate_max`, it is replaced by `bank_mortgage_rate_mid`
  - If the down payment is below the standard benchmark, it is NOT replaced (asymmetry: favorable down payment is preserved)
  - The term is kept the same
  - The financed amount is kept the same
- The theoretical total cost at benchmark is computed
- `overcost_vs_benchmark_usd = total_cost_paid - total_cost_at_benchmark`
- If `overcost_vs_benchmark_usd > 0`, it is recorded with magnitude and the list of changes that would produce the savings
- If `overcost_vs_benchmark_usd ≤ 0`, `no_overcost` is noted with a favorable tone
- The computation is traceable: F5 produces both amortizations (contract and benchmark) so the report can show them side by side

### US-06: System detects inconsistencies and missing data

**As the** system,
**I want to** detect when the contract has incoherent or missing figures,
**So that** F4 can generate specific findings.

**Acceptance criteria:**

- F5 emits structured warnings that F4 can translate into findings:
  - `monthly_payment_higher_than_theoretical`: payment is 5%+ higher than pure amortization suggests hidden costs
  - `down_payment_inconsistent`: percentage and absolute amount do not match
  - `interest_calculation_base_unfavorable`: computation base is total balance, not outstanding principal
  - `total_cost_not_disclosed`: the contract does not state the total cost
  - `annual_rate_not_expressed`: rate is expressed only as monthly, without effective annual equivalent
  - `term_excessive`: term exceeds the legal or reasonable maximum
- Each warning includes: code, description, suggested severity (`yellow` or `red`), `related_field`
- F4 consumes them and decides whether to generate findings; F5 does not generate findings directly

### US-07: System produces the complete `EconomicSummary`

**As the** system,
**I want to** persist the economic-analysis result in `ContractAnalysis`,
**So that** F4 consumes it and F6 displays it in the report.

**Acceptance criteria:**

- F5 writes `ContractAnalysis.economic_summary` (JSONB) with the complete structure
- F5 also writes `ContractAnalysis.benchmark_version` with the version used
- The fields of `EconomicSummary` follow the structure defined in `DOMAIN_MODEL.md` §5.5
- Persistence is atomic with the rest of the analysis
- If F5 fails and does not produce a summary, the field remains `null` and F4 evaluates economic criteria as unverifiable

**Expected structured output:**

```json
{
    "contract_type": "CVP",
    "currency": "USD",
    "currency_conversion_note": null,
    "fields_extracted": {
        "price_cash": 80000,
        "down_payment": 8000,
        "down_payment_pct": 0.10,
        "financed_amount": 72000,
        "term_months": 240,
        "annual_rate_pct": 0.18,
        "monthly_rate_pct": 0.015,
        "monthly_payment": 1083.50,
        "payment_periodicity": "monthly",
        "interest_calculation_base": "total_balance"
    },
    "fields_derived": {
        "total_cost_paid": 268040,
        "total_cost_vs_cash_multiplier": 3.35,
        "monthly_payment_theoretical": 1083.50,
        "monthly_payment_coherent": true
    },
    "benchmark_comparisons": [
        {
            "metric": "annual_rate",
            "metric_label": "Effective annual rate",
            "contract_value": 0.18,
            "benchmark_value": 0.09,
            "benchmark_key": "bank_mortgage_rate_mid",
            "benchmark_source": "BCR, active rates, 2026-Q2",
            "delta_pct_points": 9.0,
            "assessment": "well_above_market"
        }
    ],
    "overcost": {
        "vs_benchmark_usd": 95000,
        "explanation": "If the rate were 9% instead of 18%, you would pay $173,040 in total. Today the contract charges you $268,040.",
        "what_changes_would_save": [
            "Reduce the annual rate from 18% to 9% (standard banking-market rate)"
        ]
    },
    "warnings": [
        {
            "code": "interest_calculation_base_unfavorable",
            "severity_suggested": "red",
            "description": "Interest is computed on the total balance, not on outstanding principal. This violates Art. 12 LPC.",
            "related_field": "interest_calculation_base"
        }
    ],
    "benchmark_version": "2026-Q2"
}
```

---

## 4. Business Rules

**BR-01:** Benchmarks are versioned. Each analysis records the `benchmark_version` it used. Benchmark changes do not affect previous analyses.

**BR-02:** Penalty is asymmetric. A contract metric better than the benchmark NEVER generates a warning or penalty. A 5% down payment where the benchmark is 10% does not concern F5.

**BR-03:** When there is ambiguity in field extraction (low confidence, multiple values), F5 assumes the reasonable worst case for the buyer. For example, if the rate is expressed ambiguously, the interpretation that produces the higher cost is taken.

**BR-04:** Currency conversions use a fixed exchange rate. For colones to USD, ¢8.75 = $1 is used (official historical parity). Real-time exchange rates are not consulted.

**BR-05:** Monthly-to-annual rate conversions assume monthly compounding: `annual = (1 + monthly)^12 - 1`. `annual = monthly × 12` is not used (that is nominal, not effective).

**BR-06:** Amortization computations use the standard French formula. F5 does not support German, American amortization, or graduated installments unless the contract makes it explicit (which is rare in El Salvador for housing).

**BR-07:** The coherence cross-check tolerance is 5%. If the contract's monthly payment differs by more than 5% from the theoretical installment, a warning is noted but the value is not rejected.

**BR-08:** F5 warnings are suggestions to F4, not decisions. F4 re-evaluates the criterion with its own prompt.

**BR-09:** If F5 cannot compute any derived field due to missing data, it writes `economic_summary` with empty `fields_extracted` and `derivation_status: "insufficient_data"`. F4 will see it and mark economic criteria as unverifiable.

**BR-10:** Overcost is computed against the applicable segment benchmark, not the best possible benchmark. For a CVP contract directly with developer, the benchmark is the direct-developer range, not the bank range.

**BR-11:** When the contract is FSV and the contract's rate falls within the published FSV range, no overcost is computed against the bank range; it is evaluated only against FSV.

**BR-12:** Expired benchmarks (`next_review_due < today`) generate an operational alert but do NOT block the analysis. The last value continues to be used with a note in the report about the update date.

**BR-13:** F5 does not call the LLM. It is deterministic logic with configuration. This guarantees pure reproducibility.

**BR-14:** Currency-exchange conversion is applied only if the contract explicitly declares colones. If it declares USD, USD is kept. If no currency is declared and values are consistent with USD (typical in El Salvador), USD is assumed and noted.

---

## 5. Data Models

### 5.1 EconomicBenchmark catalog (defined in F8, fed from YAML)

```sql
CREATE TABLE economic_benchmark (
    benchmark_key TEXT NOT NULL,
    benchmark_version TEXT NOT NULL,

    value_min NUMERIC(10,4),
    value_max NUMERIC(10,4),
    value_default NUMERIC(10,4),
    unit TEXT NOT NULL CHECK (unit IN ('pct', 'usd', 'months', 'multiplier', 'ratio')),

    applicable_contract_types TEXT[] NOT NULL,

    source TEXT NOT NULL,
    source_url TEXT,
    last_updated DATE NOT NULL,
    next_review_due DATE NOT NULL,

    notes TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (benchmark_key, benchmark_version)
);

CREATE INDEX idx_benchmark_version ON economic_benchmark(benchmark_version);
CREATE INDEX idx_benchmark_types ON economic_benchmark USING GIN(applicable_contract_types);
```

### 5.2 Benchmark version catalog

```sql
CREATE TABLE benchmark_version (
    version TEXT PRIMARY KEY,
    released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    benchmark_count INTEGER NOT NULL,
    changelog TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_benchmark_version_active ON benchmark_version(is_active) WHERE is_active = TRUE;
```

### 5.3 Updates to `contract_analysis` written by F5

```sql
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS economic_summary JSONB;
ALTER TABLE contract_analysis ADD COLUMN IF NOT EXISTS benchmark_version TEXT REFERENCES benchmark_version(version);
```

---

## 6. Integration Points

### 6.1 Input: queue from F2

F5 consumes the same message as F4 (published by F2):

```json
{
    "submission_id": "uuid",
    "analysis_id": "uuid",
    "project_id": "uuid",
    "extracted_text": "...",
    "classification": { },
    "economic_fields_raw": { },
    "elements_detected": { }
}
```

F5 only processes if `classification.contract_type` is in `{CVP, APV, LEA, FSV, ARV}` (the types with relevant economic figures). For CVC cash, IVU, ARC, a reduced version runs (only total price and one-time costs if any).

### 6.2 Output: queue to F4

F5 publishes when finished:

```json
{
    "analysis_id": "uuid",
    "economic_summary": { },
    "benchmark_version": "2026-Q2",
    "warnings": [ ]
}
```

F4 waits for both its own normal processing and F5's result before closing the score.

### 6.3 Configuration

- `BENCHMARK_FILE_PATH` env var (default `/etc/casa-segura/economic_benchmarks.yaml`)
- `BENCHMARK_RELOAD_ON_SIGHUP` env var (default true; allows reload without restart)
- `EXCHANGE_RATE_USD_PER_SVC` env var (default 0.114285714; equivalent to 8.75 SVC/USD)
- `BENCHMARK_EXPIRED_ALERT_DAYS` env var (default 30; alerts if a benchmark expires in fewer than N days)

### 6.4 Structure of the `economic_benchmarks.yaml` file

```yaml
# economic_benchmarks.yaml
# Version: 2026-Q2
# Release date: 2026-04-01
# Next review: 2026-07-01
# Approved by: [curation owner]

version: "2026-Q2"
released_at: "2026-04-01"
next_review_due: "2026-07-01"

benchmarks:
  standard_down_payment_bank_purchase:
    value_default: 0.10
    unit: pct
    applicable_contract_types: [CVP, FSV]
    source: "ABANSA — Lineamientos de crédito hipotecario"
    source_url: "https://www.abansa.org.sv/..."
    last_updated: "2026-01-15"
    next_review_due: "2026-07-15"
    notes: "Standard 10% down payment in Salvadoran banking mortgage credit."

  bank_mortgage_rate_min:
    value_default: 0.07
    unit: pct
    applicable_contract_types: [CVP, FSV]
    source: "BCR — Tasas de interés activas por tipo de crédito"
    source_url: "https://www.bcr.gob.sv/..."
    last_updated: "2026-03-01"
    next_review_due: "2026-06-01"

  bank_mortgage_rate_max:
    value_default: 0.09
    unit: pct
    applicable_contract_types: [CVP, FSV]
    source: "BCR — Tasas de interés activas por tipo de crédito"
    source_url: "https://www.bcr.gob.sv/..."
    last_updated: "2026-03-01"
    next_review_due: "2026-06-01"

  bank_mortgage_rate_mid:
    value_default: 0.08
    unit: pct
    applicable_contract_types: [CVP, FSV]
    source: "Average of min and max"
    last_updated: "2026-03-01"
    next_review_due: "2026-06-01"

  developer_direct_rate_min:
    value_default: 0.08
    unit: pct
    applicable_contract_types: [CVP, APV, LEA]
    source: "Market observation by real estate trade association"
    last_updated: "2026-02-10"
    next_review_due: "2026-08-10"

  developer_direct_rate_max:
    value_default: 0.12
    unit: pct
    applicable_contract_types: [CVP, APV, LEA]
    source: "Market observation by real estate trade association"
    last_updated: "2026-02-10"
    next_review_due: "2026-08-10"

  credit_term_max_reasonable:
    value_default: 300  # 25 years
    unit: months
    applicable_contract_types: [CVP, APV, LEA, FSV]
    source: "Standard banking practice"
    last_updated: "2026-01-01"
    next_review_due: "2027-01-01"

  credit_term_ivu_max:
    value_default: 360  # 30 years
    unit: months
    applicable_contract_types: [IVU]
    source: "Art. 2 Ley sobre Contratos del IVU"
    last_updated: "1986-03-18"  # last Art. 2 reform date
    next_review_due: "2030-01-01"
    notes: "Set by law, not by market. Would only change with legal reform."

  cost_multiplier_healthy_max:
    value_default: 1.5
    unit: ratio
    applicable_contract_types: [CVP, APV, LEA, FSV]
    source: "Standard financial calculation"
    last_updated: "2026-01-01"
    next_review_due: "2027-01-01"

  cost_multiplier_excessive_min:
    value_default: 2.5
    unit: ratio
    applicable_contract_types: [CVP, APV, LEA, FSV]
    source: "Standard financial calculation"
    last_updated: "2026-01-01"
    next_review_due: "2027-01-01"
```

---

## 7. API Surface

F5 does not expose public HTTP endpoints.

For QA the following is exposed:

### 7.1 `POST /v1/internal/economic/analyze` (requires `X-Internal-Auth`)

```json
{
    "contract_type": "CVP",
    "economic_fields_raw": { }
}
```

**Response:**

```json
{
    "economic_summary": { },
    "warnings": [ ],
    "benchmark_version_used": "2026-Q2",
    "elapsed_ms": 12
}
```

### 7.2 `GET /v1/internal/economic/benchmarks` (requires `X-Internal-Auth`)

Lists benchmarks of the active version.

---

## 8. LLM Prompts

F5 does not use an LLM. It is pure deterministic logic.

---

## 9. Non-Functional Requirements

- **P50 latency:** under 50 ms (pure CPU computations).
- **P95 latency:** under 200 ms.
- **Determinism:** same inputs always produce same outputs.
- **Availability:** depends only on the database for reading benchmarks; target 99.9%.
- **Benchmark file load:** under 100 ms at startup.
- **Hot reload support:** reload benchmark file without restarting the service (SIGHUP).
- **Observability:** Prometheus metrics for assessment distribution per benchmark, age of the active benchmark, rate of fields not extracted by F2.
- **Test coverage:** over 95% unit test coverage given the deterministic nature of the feature.

---

## 10. Open Questions

1. Is the fixed ¢8.75/USD parity maintained as the only conversion? The colón is officially out of circulation since 2001 but old contracts may cite it. The historical parity is 8.75; we could accept documented variations.

2. How are contracts in other currencies (Euro, Mexican, Guatemalan) handled? Rare in El Salvador but possible. Proposal: reject with `currency_not_supported` and defer to v2.

3. Should the rate benchmark consider the buyer's stratum? Banks charge different rates by risk. Without knowing the user's profile, F5 uses the median rate. Is that correct?

4. How are contracts with graduated installments handled? Common in some products. For now F5 assumes a fixed installment; graduated installments are marked `unsupported_payment_schedule` and evaluated as unverifiable.

5. Should overcost computation assume savings reinvestment? If the buyer saved $X per month with a cheaper credit, they could invest it. The current computation does not consider time-value of money beyond the implicit amortization discount. Worth it?

6. Who reviews and updates the `economic_benchmarks.yaml` file? Without a formal update process, benchmarks go stale. Product must define frequency and owner.

7. Should F5 warnings be exhaustive or prioritized? If the contract has 8 economic inconsistencies, do we generate 8 warnings or consolidate? F4 translates them into findings, so consolidating may be wise to avoid flooding the report.

8. Should the system allow a user to contribute their own benchmark (e.g. "I have a preapproval at X% from bank Y")? Not today; could be a future feature. For now F5 only uses catalog benchmarks.

---

**End of document.**
