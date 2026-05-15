# Solution Diagrams — F5: Economic Analysis & Benchmarks

> Generated: 2026-05-15

---

## 1. Class Diagram

### 1.1 Domain + Application

```mermaid
classDiagram
    class EconomicSummary { <<Pydantic>> }
    class ExtractedFields { <<Pydantic>> }
    class DerivedFields { <<Pydantic>> }
    class BenchmarkComparison { <<Pydantic>> }
    class Overcost { <<Pydantic>> }
    class EconomicWarning { <<Pydantic>> }
    class BenchmarkVersion { <<Pydantic>> }
    class EconomicBenchmark { <<Pydantic>> }
    class ComputeEconomicSummary {
        <<Command>>
        +UUID analysis_id
        +EconomicFieldsRaw raw_fields
        +ContractType contract_type
    }
    class LoadBenchmarks {
        <<Command>>
        +str version
    }
    class ActivateBenchmarks {
        <<Command>>
        +str version
    }
    class GetActiveBenchmarkVersion {
        <<Query>>
    }
    class GetBenchmarksFor {
        <<Query>>
        +str benchmark_version
        +ContractType contract_type
    }
    class economic_handlers {
        <<handlers>>
        +compute_summary(cmd) EconomicSummary
        +load_benchmarks(cmd) None
        +activate_benchmarks(cmd) None
    }
    class EconomicAnalysisService {
        -BenchmarkRepository repo
        -BenchmarkVersionRepository ver_repo
        -ContractAnalysisRepository analysis_repo
        +compute(analysis_id, raw, contract_type) EconomicSummary
        -normalize(raw) ExtractedFields
        -derive(extracted) DerivedFields
        -compare(extracted, derived, benchmarks, contract_type) list~BenchmarkComparison~
        -compute_overcost(...) Overcost|None
        -emit_warnings(extracted, derived, comparisons) list~EconomicWarning~
    }
    class BenchmarkLoader {
        +load_yaml(path) ParsedBenchmarks
        +validate(parsed) None
    }
    class FrenchAmortization {
        +monthly_payment(financed, annual_rate, term_months) float
        +total_cost(financed, monthly, term) float
    }
    class CurrencyConverter {
        +to_usd(value, currency) float
    }
    EconomicAnalysisService *-- FrenchAmortization
    EconomicAnalysisService *-- CurrencyConverter
    economic_handlers ..> ComputeEconomicSummary
    economic_handlers ..> LoadBenchmarks
    economic_handlers ..> ActivateBenchmarks
```

### 1.2 Infrastructure

```mermaid
classDiagram
    class BenchmarkVersionModel { <<Django Model>> }
    class EconomicBenchmarkModel { <<Django Model>> }
    class BenchmarkRepository { <<DjangoFullRepository>> }
    class BenchmarkVersionRepository { <<DjangoFullRepository>> }
    class ContractAnalysisRepository {
        <<DjangoFullRepository>>
        +persist_economic_summary(analysis_id, summary, version) None
    }
    class EconomicConsumer { <<Redis Streams consumer>> }
    class ComputeEconomicSummaryTask { <<Celery shared_task>> }
    class BenchmarksLoadCommand { <<management command>> }
    class BenchmarksActivateCommand { <<management command>> }
    class InternalAnalyzeView { <<DRF APIView>> }
    class InternalBenchmarksView { <<DRF APIView>> }
    BenchmarkRepository ..> EconomicBenchmarkModel
    ComputeEconomicSummaryTask ..> EconomicAnalysisService
    EconomicConsumer ..> ComputeEconomicSummaryTask
    InternalAnalyzeView ..> EconomicAnalysisService
    BenchmarksLoadCommand ..> BenchmarkLoader
```

---

## 2. Sequence Diagrams

### 2.1 Compute summary (happy path)

```mermaid
sequenceDiagram
    participant Q as Stream classification.to_rubric_and_economics (group economics)
    participant C as EconomicConsumer
    participant T as ComputeEconomicSummaryTask
    participant S as EconomicAnalysisService
    participant BR as BenchmarkRepository
    participant AR as ContractAnalysisRepository

    Q-->>C: XREADGROUP envelope (ClassificationDone)
    C->>T: economics.compute_summary.delay(analysis_id, raw_fields_json, contract_type)
    T->>S: compute(analysis_id, raw, contract_type)
    S->>S: normalize raw fields (currency, %, term, rates)
    S->>S: derive financed_amount, total_cost, monthly_payment_theoretical
    S->>S: coherence cross-check (5%)
    S->>BR: get_for(version=active, contract_type)
    BR-->>S: list[EconomicBenchmark]
    S->>S: build BenchmarkComparison per metric (asymmetric assessments)
    S->>S: compute overcost (FrenchAmortization at benchmark rate)
    S->>S: emit warnings
    S->>AR: persist_economic_summary(analysis_id, summary, benchmark_version)
    AR-->>S: ok
    Note over S,AR: F4 watermark check now sees economic_summary; barrier releases
```

### 2.2 Insufficient data path

```mermaid
sequenceDiagram
    participant S as EconomicAnalysisService
    participant AR as ContractAnalysisRepository

    S->>S: raw fields all null
    S->>S: build EconomicSummary(derivation_status="insufficient_data", fields_extracted=empty, warnings=[])
    S->>AR: persist
    Note over S: F4 will see economic_summary, evaluate economic criteria as unverifiable per BR-15
```

### 2.3 Benchmark load

```mermaid
sequenceDiagram
    actor Op as Operator
    participant Cmd as BenchmarksLoadCommand
    participant Loader as BenchmarkLoader
    participant Repo as BenchmarkRepository
    participant Ver as BenchmarkVersionRepository

    Op->>Cmd: python manage.py benchmarks_load --version 2026-Q2 --path economics/benchmarks/2026-Q2.yaml
    Cmd->>Loader: load_yaml(path)
    Loader-->>Cmd: ParsedBenchmarks(N rows)
    Cmd->>Ver: get_by_version("2026-Q2")
    Ver-->>Cmd: None
    Cmd->>Repo: bulk_create(EconomicBenchmark rows, version="2026-Q2")
    Cmd->>Ver: save(BenchmarkVersion(version="2026-Q2", benchmark_count=N, is_active=False))
```

---

## 3. State Diagram — BenchmarkVersion

```mermaid
stateDiagram-v2
    [*] --> draft: YAML edited
    draft --> loaded: benchmarks_load
    loaded --> active: benchmarks_activate
    active --> deactivated: new version activated
    deactivated --> active: re-activate (rare)
```

---

## 4. Activity Diagram

```mermaid
flowchart TD
    A[Receive ClassificationDone] --> B{contract_type in CVP,APV,LEA,FSV,ARV?}
    B -->|no| C[Minimal summary: price_cash only; derivation_status=partial]
    B -->|yes| D[Normalize fields]
    D --> E[Derive total_cost, theoretical monthly]
    E --> F[Coherence cross-check 5%]
    F --> G[Load benchmarks for active version + contract_type]
    G --> H[Build BenchmarkComparison per metric with asymmetric assessment]
    H --> I[Compute overcost via French amortization at benchmark rate]
    I --> J[Emit warnings]
    C --> K[Persist economic_summary on contract_analysis]
    J --> K
    K --> L[End: F4 watermark released]
```

---

## 5. Component Diagram

```mermaid
graph TD
    YAML[economics/benchmarks/*.yaml]
    Loader[BenchmarkLoader]
    Cmd[benchmarks_load / activate]
    Repo[BenchmarkRepository]
    PG[(Postgres)]
    Cons[EconomicConsumer]
    Task[ComputeEconomicSummaryTask]
    Svc[EconomicAnalysisService]
    AR[ContractAnalysisRepository]
    F4[F4 watermark waits on economic_summary]
    Internal[InternalAnalyzeView]

    YAML --> Loader --> Cmd --> Repo --> PG
    Cons --> Task --> Svc
    Svc --> Repo
    Svc --> AR --> PG
    AR -.unblocks.-> F4
    Internal --> Svc
```

---

## 6. Use Case Diagram

```mermaid
graph LR
    F2sys[F2 worker]
    Op[Operator]
    QA[QA]
    F2sys --> UC1((Compute economic summary))
    Op --> UC2((Load benchmark version))
    Op --> UC3((Activate benchmark version))
    QA --> UC4((Analyze raw fields directly))
    Op --> UC5((List benchmarks of active version))
```

**End of document.**
