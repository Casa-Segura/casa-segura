# Interaction Diagrams — F5: Economic Analysis & Benchmarks

> Generated: 2026-05-15

---

## Component Overview

```mermaid
graph TD
    F2Stream[Stream classification.to_rubric_and_economics group economics]
    Cons[EconomicConsumer]
    Task[ComputeEconomicSummaryTask]
    Svc[EconomicAnalysisService]
    Repo[BenchmarkRepository]
    AR[ContractAnalysisRepository]
    PG[(Postgres)]
    F4[F4 barrier waits on economic_summary]

    F2Stream --> Cons --> Task --> Svc
    Svc --> Repo --> PG
    Svc --> AR --> PG
    AR -.releases.-> F4
```

---

## Flow: US-01 Validate and normalize

```mermaid
sequenceDiagram
    participant S as EconomicAnalysisService
    participant CC as CurrencyConverter

    S->>S: receive raw fields (each with value, confidence, evidence_snippet)
    loop for each field
        S->>S: if confidence < 0.5 or value null → mark not_present
        S->>S: if currency=SVC → CC.to_usd
        S->>S: if value out of range → mark invalid
    end
    S->>S: ExtractedFields built
```

---

## Flow: US-02 Derive fields

```mermaid
sequenceDiagram
    participant S as EconomicAnalysisService
    participant F as FrenchAmortization

    S->>S: if monthly_rate_pct only → annual = (1+m)^12 - 1
    S->>S: financed_amount = price - down_payment
    alt term + monthly_payment + financed present
        S->>S: total_cost_paid = down + monthly * term
        S->>S: total_cost_vs_cash_multiplier = total_cost / price
    end
    alt rate + term + financed present
        S->>F: monthly_payment(financed, annual_rate, term)
        F-->>S: theoretical_monthly
        S->>S: monthly_payment_coherent = abs(extracted - theoretical) / theoretical <= 0.05
    end
```

---

## Flow: US-03 Load benchmarks

```mermaid
sequenceDiagram
    actor Op as Operator
    participant Cmd as BenchmarksLoadCommand
    participant L as BenchmarkLoader
    participant Repo as BenchmarkRepository
    participant Ver as BenchmarkVersionRepository

    Op->>Cmd: python manage.py benchmarks_load --version 2026-Q2 --path economics/benchmarks/2026-Q2.yaml
    Cmd->>L: load_yaml(path)
    L-->>Cmd: parsed
    Cmd->>L: validate(parsed)
    Cmd->>Repo: bulk_create(rows)
    Cmd->>Ver: save(BenchmarkVersion is_active=False)
```

---

## Flow: US-04 Build benchmark comparisons

```mermaid
sequenceDiagram
    participant S as EconomicAnalysisService

    S->>S: for each metric (annual_rate, down_payment_pct, term_months, cost_multiplier, monthly_payment)
    S->>S: lookup applicable benchmark by key + contract_type
    S->>S: compute delta_pct_points (or delta_absolute for non-pct)
    S->>S: assess: below_market_favorable (asymmetric) / within / slightly_above / above / well_above
    S->>S: append BenchmarkComparison
```

Rate assessment rule (illustrative):

```text
delta = (contract_rate - benchmark_mid) * 100  # pct points
if delta < 0  → below_market_favorable
if 0 <= delta < 1 → within_market
if 1 <= delta < 2 → slightly_above_market
if 2 <= delta < 5 → above_market
if delta >= 5 → well_above_market
```

---

## Flow: US-05 Compute overcost

```mermaid
sequenceDiagram
    participant S as EconomicAnalysisService
    participant F as FrenchAmortization

    S->>S: substitutions = {annual_rate: bank_mortgage_rate_mid if annual_rate > bank_mortgage_rate_max else annual_rate}
    Note over S: down payment NOT substituted (asymmetry)
    S->>F: monthly_payment(financed, substituted_rate, term)
    F-->>S: theoretical_monthly_at_benchmark
    S->>S: theoretical_total = down + theoretical_monthly * term
    S->>S: overcost_usd = contract_total_cost - theoretical_total
    alt overcost > 0
        S->>S: build Overcost with explanation + changes list
    else
        S->>S: Overcost = None ("no_overcost")
    end
```

---

## Flow: US-06 Emit warnings

```mermaid
sequenceDiagram
    participant S as EconomicAnalysisService

    S->>S: if monthly_payment_coherent == false → warning monthly_payment_higher_than_theoretical
    S->>S: if extracted.down_payment_pct present and abs(down/price - dpct) > 0.05 → down_payment_inconsistent
    S->>S: if interest_calculation_base == "total_balance" → interest_calculation_base_unfavorable (red)
    S->>S: if total_cost not deducible → total_cost_not_disclosed
    S->>S: if annual_rate_pct missing and monthly_rate_pct missing → annual_rate_not_expressed
    S->>S: if term_months > credit_term_max_reasonable → term_excessive
```

---

## Flow: US-07 Persist EconomicSummary

```mermaid
sequenceDiagram
    participant S as EconomicAnalysisService
    participant AR as ContractAnalysisRepository
    participant PG as Postgres
    participant F4 as F4 watermark check

    S->>AR: persist_economic_summary(analysis_id, summary, benchmark_version)
    AR->>PG: UPDATE contract_analysis SET economic_summary=$1, benchmark_version=$2 WHERE id=$3
    PG-->>AR: ok
    F4->>PG: SELECT economic_summary FROM contract_analysis WHERE id=$1 (next poll)
    PG-->>F4: not null
    Note over F4: barrier released
```

---

## Class Diagram

```mermaid
classDiagram
    class EconomicAnalysisService
    class BenchmarkLoader
    class FrenchAmortization
    class CurrencyConverter
    class BenchmarkRepository
    class BenchmarkVersionRepository
    class ContractAnalysisRepository
    class ComputeEconomicSummaryTask
    class EconomicConsumer
    class InternalAnalyzeView
    class InternalBenchmarksView

    EconomicAnalysisService *-- FrenchAmortization
    EconomicAnalysisService *-- CurrencyConverter
    EconomicAnalysisService o-- BenchmarkRepository
    EconomicAnalysisService o-- BenchmarkVersionRepository
    EconomicAnalysisService o-- ContractAnalysisRepository
    ComputeEconomicSummaryTask ..> EconomicAnalysisService
    EconomicConsumer ..> ComputeEconomicSummaryTask
    InternalAnalyzeView ..> EconomicAnalysisService
```

**End of document.**
