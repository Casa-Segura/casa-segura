# Interaction Diagrams — F2: Contract Classification & Structured Extraction

> Generated: 2026-05-15
> Companion to `SOLUTION_DIAGRAMS.md`.

---

## Component Overview

```mermaid
graph TD
    F1Stream[Redis Stream ingestion.to_classification]
    Cons[ClassificationConsumer daemon]
    Task[Celery process_classification]
    Svc[ClassificationService]
    LLM[OpenRouterClient]
    AnaRepo[ContractAnalysisRepository]
    ProjRepo[ProjectRepository]
    JobRepo[ClassificationJobRepository]
    Pub[ClassificationStreamPublisher]
    F4F5Stream[Redis Stream classification.to_rubric_and_economics]
    PG[(Postgres)]

    F1Stream --> Cons --> Task --> Svc
    Svc --> LLM
    Svc --> AnaRepo --> PG
    Svc --> ProjRepo --> PG
    Svc --> JobRepo --> PG
    Svc --> Pub --> F4F5Stream
```

---

## Flow: US-01 Classification — confidence high

```mermaid
sequenceDiagram
    participant Q as Stream ingestion.to_classification
    participant C as ClassificationConsumer
    participant T as ProcessClassificationTask
    participant S as ClassificationService
    participant L as OpenRouterClient
    participant PR as ProjectRepository
    participant AR as ContractAnalysisRepository
    participant JR as ClassificationJobRepository
    participant P as ClassificationStreamPublisher

    Q-->>C: XREADGROUP message
    C->>T: process_classification.delay(envelope)
    T->>S: classify(envelope)
    S->>JR: create_classification_job(step=classification, status=running)
    JR-->>S: job_id
    S->>L: chat_completion_json(model, prompt §8.1, key=sub:f2:classification)
    L-->>S: { contract_type: "CVP", confidence: 0.92, project_name_canonical: "...", elements_detected: {...} }
    S->>JR: complete_classification_job(job_id, status=success, tokens, cost)
    S->>JR: create_classification_job(step=economic_extraction)
    S->>L: chat_completion_json(prompt §8.5, key=sub:f2:economic_extraction)
    L-->>S: { economic_fields: {...} }
    S->>JR: complete_classification_job(success)
    S->>S: normalize project name
    S->>PR: upsert_project(canonical, normalized)
    PR-->>S: project_id
    S->>AR: update_classification(analysis_id, result, project_id)
    AR-->>S: ok
    S->>P: publish_classification_done(envelope)
    P-->>S: ok
```

---

## Flow: US-02 Reclassification CVP → LEA

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant L as OpenRouterClient
    participant JR as ClassificationJobRepository

    S->>S: type = CVP (from US-01)
    S->>JR: create_classification_job(step=leasing_detection)
    S->>L: chat_completion_json(prompt §8.4, key=sub:f2:leasing)
    L-->>S: { indicators_count: 5, should_reclassify: true, leasing_indicators: {...} }
    S->>JR: complete_classification_job(success)
    S->>S: result.contract_type = LEA
    S->>S: result.contract_type_declared = CVP
    S->>S: result.contract_type_reclassified = true
    S->>S: result.reclassification_reason = "5 of 6 Art. 2 LAF indicators present: mandatory_term, ..."
```

---

## Flow: US-03 Validation retry on medium confidence

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant L as OpenRouterClient
    participant JR as ClassificationJobRepository

    S->>L: chat_completion_json(prompt §8.1, key=sub:f2:classification, attempt=1)
    L-->>S: confidence 0.72, type APV
    S->>JR: create_classification_job(step=classification, attempt_number=2)
    S->>L: chat_completion_json(prompt §8.3 validation, key=sub:f2:classification_validation, attempt=2)
    L-->>S: confidence 0.79, type APV (agrees)
    S->>S: accept; classification_attempts=2
```

### Disagreement branch

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant L as OpenRouterClient
    participant AR as ContractAnalysisRepository

    S->>L: validation attempt
    L-->>S: type ARV (differs from prior APV)
    S->>S: mark NOT_CLASSIFIABLE
    S->>AR: update_classification(contract_type=NOT_CLASSIFIABLE, classification_confidence=0.75, classification_attempts=2)
    Note over S: No publication to F4/F5
```

---

## Flow: US-04 Economic field extraction

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant L as OpenRouterClient

    S->>S: type in {CVP, APV, LEA, FSV, ARV} → run economic
    S->>L: chat_completion_json(prompt §8.5, key=sub:f2:economic_extraction)
    L-->>S: { price_cash: {value:80000,...}, down_payment_pct: {value:0.10,...}, annual_rate_pct: {value:0.18, evidence_snippet: "1.5% mensual", extraction_note:"converted from monthly"}, interest_calculation_base: {value:"total_balance"} }
    S->>S: detect interest_calculation_base == total_balance → flag for F4 as potential art_12_lpc override
```

---

## Flow: US-05 Element detection (part of classification call)

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant L as OpenRouterClient

    Note over S,L: elements_detected is part of the classification §8.1 response, not a separate call
    L-->>S: ..., elements_detected: {warranty_clause: true, warranty_exemption_clause: false, bien_de_familia_mention: false, ...}
    Note over S: These are hints, not decisions. F4 re-evaluates with its own prompt.
```

---

## Flow: US-06 NOT_CLASSIFIABLE clean rejection

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant AR as ContractAnalysisRepository
    participant SubRepo as ContractSubmissionRepository
    participant Zavu as ZavuClient
    participant Email as F7DeliveryService

    S->>S: confidence < 0.65 OR LLM says NOT_CLASSIFIABLE
    S->>AR: update_classification(contract_type=NOT_CLASSIFIABLE)
    S->>SubRepo: update_status(submission_id, processing_status=rejected_type, error_code=TYPE_NOT_SUPPORTED, error_reason="...")
    alt source = web
        Note over S: status endpoint will return rejected_type on next poll
    else source = whatsapp
        S->>Zavu: send_message(template=not_classifiable, params={short_id})
    end
```

---

## Class Diagram (high-level)

```mermaid
classDiagram
    class ClassificationService
    class ClassificationResult
    class LeasingIndicators
    class ElementsDetected
    class EconomicFieldsRaw
    class ProjectNameNormalizer
    class OpenRouterClient
    class ContractAnalysisRepository
    class ProjectRepository
    class ClassificationJobRepository
    class ProcessClassificationTask
    class ClassificationConsumer
    class ClassificationStreamPublisher
    class InternalClassifyView

    ClassificationService *-- ProjectNameNormalizer
    ClassificationService o-- OpenRouterClient
    ClassificationService o-- ContractAnalysisRepository
    ClassificationService o-- ProjectRepository
    ClassificationService o-- ClassificationJobRepository
    ClassificationService o-- ClassificationStreamPublisher
    ProcessClassificationTask ..> ClassificationService
    ClassificationConsumer ..> ProcessClassificationTask
    InternalClassifyView ..> ClassificationService
    ClassificationService ..> ClassificationResult
    ClassificationResult o-- LeasingIndicators
    ClassificationResult o-- ElementsDetected
    ClassificationResult o-- EconomicFieldsRaw
```

---

## Notes

- The `ClassificationConsumer` daemon runs as its own process (`python manage.py run_classification_consumer`). It reads from the Redis stream with `XREADGROUP`, `XACK`s after successfully dispatching the Celery task. Failures during dispatch park the message for re-read.
- All LLM calls are wrapped by the same `OpenRouterClient` (with circuit breaker shared across F1 and F2). When the breaker opens, classification fails fast with `LLM_AUTH_FAILED` or `LLM_TRANSIENT_FAILURE` and the submission goes to `failed_classification`.
- Project upsert uses Postgres `INSERT ... ON CONFLICT (normalized_name) DO UPDATE SET last_analyzed = NOW(), canonical_name = EXCLUDED.canonical_name RETURNING id`. The `total_analyses` increment is left to F8's `recompute_project_metrics` cron so F2's transaction stays narrow.

**End of document.**
