# Solution Diagrams — F2: Contract Classification & Structured Extraction

> Generated: 2026-05-15
> UML diagrams. Companion: `INTERACTION_DIAGRAMS.md` for per-flow detail.

---

## 1. Class Diagram (UML)

### 1.1 Domain + Application layer

```mermaid
classDiagram
    class ContractType {
        <<TextChoices>>
        CVC
        CVP
        ARV
        ARC
        APV
        LEA
        IVU
        FSV
        NOT_CLASSIFIABLE
    }

    class IndicatorDetection {
        <<Pydantic BaseModel>>
        +bool detected
        +str|None evidence
    }

    class LeasingIndicators {
        <<Pydantic BaseModel>>
        +IndicatorDetection mandatory_term
        +IndicatorDetection predefined_purchase_option
        +IndicatorDetection ownership_retained
        +IndicatorDetection taxes_to_buyer
        +IndicatorDetection risks_to_buyer
        +IndicatorDetection payments_as_rent
        +int indicators_count
        +bool should_reclassify
        +str reclassification_severity
    }

    class ElementsDetected {
        <<Pydantic BaseModel>>
        +bool warranty_clause
        +bool warranty_exemption_clause
        +bool bien_de_familia_mention
        +bool fsv_mention
        +bool urbanism_permit_mention
        +bool promise_to_sell
        +bool public_deed
        +bool arbitration_clause
        +bool blank_signature
        +bool rights_waiver
        +bool unilateral_modification
        +bool late_interest_on_total_balance
    }

    class EconomicFieldsRaw {
        <<Pydantic BaseModel>>
        +ExtractedNumeric|None price_cash
        +ExtractedNumeric|None down_payment
        +ExtractedNumeric|None down_payment_pct
        +ExtractedNumeric|None financed_amount
        +ExtractedNumeric|None term_months
        +ExtractedNumeric|None annual_rate_pct
        +ExtractedNumeric|None monthly_rate_pct
        +ExtractedNumeric|None monthly_payment
        +ExtractedEnum|None payment_periodicity
        +ExtractedEnum|None interest_calculation_base
    }

    class ClassificationResult {
        <<Pydantic BaseModel>>
        +ContractType contract_type
        +ContractType|None contract_type_declared
        +bool contract_type_reclassified
        +str|None reclassification_reason
        +LeasingIndicators|None reclassification_indicators
        +float classification_confidence
        +int classification_attempts
        +str|None project_name_canonical
        +str project_name_normalized
        +ElementsDetected elements_detected
        +EconomicFieldsRaw|None economic_fields_raw
    }

    class ClassificationJob {
        <<Pydantic BaseModel>>
        +UUID|None id
        +UUID submission_id
        +UUID|None analysis_id
        +ClassificationStep step
        +int attempt_number
        +str model_used
        +datetime started_at
        +datetime|None completed_at
        +ClassificationJobStatus status
        +int|None tokens_consumed
        +int|None cost_estimate_cents
        +str|None error_code
        +str|None error_message
        +datetime expires_at
    }

    class ClassifyContract {
        <<Command>>
        +UUID submission_id
        +UUID analysis_id
        +str extracted_text
    }

    class UpdateAnalysisClassification {
        <<Command>>
        +UUID analysis_id
        +ClassificationResult result
    }

    class FindOrCreateProject {
        <<Command>>
        +str canonical_name
        +str normalized_name
    }

    class CreateClassificationJob {
        <<Command>>
        +ClassificationJob job
    }

    class CompleteClassificationJob {
        <<Command>>
        +UUID job_id
        +ClassificationJobStatus status
        +int|None tokens_consumed
        +int|None cost_estimate_cents
        +str|None error_code
        +str|None error_message
    }

    class GetActiveRubricVersion {
        <<Query>>
    }

    class GetProjectByNormalizedName {
        <<Query>>
    }

    class classification_handlers {
        <<handlers>>
        +classify_contract(cmd, repo, llm) ClassificationResult
        +update_analysis(cmd, repo) None
        +find_or_create_project(cmd, repo) UUID
        +create_classification_job(cmd, repo) ClassificationJob
        +complete_classification_job(cmd, repo) ClassificationJob
    }

    class ClassificationService {
        -ContractAnalysisRepository analysis_repo
        -ProjectRepository project_repo
        -ClassificationJobRepository job_repo
        -OpenRouterClient llm
        -ClassificationStreamPublisher publisher
        -ProjectNameNormalizer normalizer
        +classify(envelope: ExtractionDone) None
        -_run_classification(text, submission_id) ClassificationResult
        -_run_validation(text, prior) ClassificationResult
        -_run_leasing_detection(text) LeasingIndicators
        -_run_economic_extraction(text) EconomicFieldsRaw
    }

    class ProjectNameNormalizer {
        +normalize(canonical: str) str
        -strip_accents(s: str) str
        -drop_generic_words(s: str) str
    }

    ClassificationResult ..> ContractType
    ClassificationResult ..> LeasingIndicators
    ClassificationResult ..> ElementsDetected
    ClassificationResult ..> EconomicFieldsRaw
    LeasingIndicators o-- IndicatorDetection
    ClassifyContract ..> str
    UpdateAnalysisClassification ..> ClassificationResult
    classification_handlers ..> ClassifyContract
    classification_handlers ..> UpdateAnalysisClassification
    classification_handlers ..> FindOrCreateProject
    classification_handlers ..> CreateClassificationJob
    classification_handlers ..> CompleteClassificationJob
    ClassificationService *-- ProjectNameNormalizer
    ClassificationService ..> classification_handlers
```

### 1.2 Infrastructure layer

```mermaid
classDiagram
    class ClassificationJobModel {
        <<Django Model>>
        +UUIDField id
        +ForeignKey submission
        +UUIDField analysis_id
        +CharField step
        +IntegerField attempt_number
        +CharField model_used
        +DateTimeField started_at
        +DateTimeField completed_at
        +CharField status
        +IntegerField tokens_consumed
        +IntegerField cost_estimate_cents
        +CharField error_code
        +TextField error_message
        +DateTimeField expires_at
    }

    class ClassificationJobRepository {
        <<DjangoFullRepository>>
        +to_entity(model) ClassificationJob
        +to_orm_model(entity) ClassificationJobModel
    }

    class ContractAnalysisRepository {
        <<DjangoFullRepository>>
        +to_entity(model) ContractAnalysis
        +to_orm_model(entity) ContractAnalysisModel
        +update_classification(analysis_id, result) None
    }

    class ProjectRepository {
        <<DjangoFullRepository>>
        +to_entity(model) Project
        +to_orm_model(entity) ProjectModel
        +upsert(canonical, normalized) Project
        +get_by_normalized_name(s) Project|None
    }

    class OpenRouterClient {
        <<reused from F1>>
        +chat_completion_json(model, prompt, idempotency_key) dict
    }

    class ClassificationConsumer {
        <<Redis Streams consumer>>
        +run_forever() None
        -dispatch_to_celery(envelope) None
    }

    class ProcessClassificationTask {
        <<Celery shared_task>>
        +run(envelope_json: str) None
    }

    class ClassificationStreamPublisher {
        +publish_classification_done(envelope) str
    }

    class InternalClassifyView {
        <<DRF APIView>>
        +post(request) Response
    }

    ClassificationJobRepository ..> ClassificationJobModel
    ClassificationJobRepository ..> ClassificationJob : maps
    ProcessClassificationTask ..> ClassificationService
    ClassificationConsumer ..> ProcessClassificationTask
    InternalClassifyView ..> ClassificationService
```

---

## 2. Sequence Diagrams (UML)

### 2.1 Happy path — CVP confidence ≥ 0.85, no reclassification

```mermaid
sequenceDiagram
    participant Q as Redis Stream ingestion.to_classification
    participant C as ClassificationConsumer
    participant T as ProcessClassificationTask (Celery)
    participant S as ClassificationService
    participant LLM as OpenRouterClient
    participant ProjRepo as ProjectRepository
    participant AnaRepo as ContractAnalysisRepository
    participant Pub as ClassificationStreamPublisher

    Q-->>C: XREADGROUP returns ExtractionDone envelope
    C->>T: process_classification.delay(envelope_json)
    T->>S: classify(envelope)
    S->>LLM: chat_completion_json(prompt §8.1/§8.2, key=sub:f2:classification)
    LLM-->>S: { contract_type: "CVP", confidence: 0.92, project_name_canonical: "Residencial Las Palmeras", elements_detected: {...} }
    S->>LLM: chat_completion_json(prompt §8.5 economic, key=sub:f2:economic_extraction)
    LLM-->>S: { price_cash: {...}, ... }
    S->>S: normalize project name → "las palmeras"
    S->>ProjRepo: upsert("Residencial Las Palmeras", "las palmeras")
    ProjRepo-->>S: Project(id=P)
    S->>AnaRepo: update_classification(analysis_id, result, project_id=P)
    AnaRepo-->>S: ok
    S->>Pub: publish_classification_done(envelope)
    Pub-->>S: stream entry id
```

### 2.2 Validation path — confidence 0.65..0.85

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant LLM as OpenRouterClient

    S->>LLM: chat_completion_json(prompt §8.1, key=sub:f2:classification)
    LLM-->>S: { contract_type: "APV", confidence: 0.72, reasoning: "..." }
    S->>LLM: chat_completion_json(prompt §8.3 validation, key=sub:f2:classification_validation)
    LLM-->>S: { contract_type: "APV", confidence: 0.81 }
    alt agree
        S->>S: accept APV, classification_attempts=2
    else disagree
        S->>S: mark NOT_CLASSIFIABLE
    end
```

### 2.3 Reclassification — CVP → LEA

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant LLM as OpenRouterClient

    S->>S: initial type = CVP, confidence 0.9
    S->>LLM: chat_completion_json(prompt §8.4 leasing detection, key=sub:f2:leasing)
    LLM-->>S: { leasing_indicators: {...}, indicators_count: 5, should_reclassify: true }
    S->>S: type ← LEA, contract_type_declared = CVP, reclassification_reason = textual list
    S->>S: contract_type_reclassified = true
```

### 2.4 NOT_CLASSIFIABLE path

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant LLM as OpenRouterClient
    participant AnaRepo as ContractAnalysisRepository

    S->>LLM: classification call
    LLM-->>S: { contract_type: "DONATION", confidence: 0.40 }
    S->>S: mark NOT_CLASSIFIABLE (confidence < 0.65 OR type out of enum)
    S->>AnaRepo: update_classification(analysis_id, contract_type="NOT_CLASSIFIABLE", classification_confidence=0.40)
    Note over S: Do NOT publish to F4/F5. The submission stops here.
    S->>S: mark contract_submission.processing_status = rejected_type, error_code = TYPE_NOT_SUPPORTED
```

### 2.5 Project name extraction fails

```mermaid
sequenceDiagram
    participant S as ClassificationService
    participant ProjRepo as ProjectRepository

    S->>S: project_name_canonical = null
    S->>S: short_hash = first 8 of submission_hash
    S->>ProjRepo: create_placeholder(normalized="unknown_<short_hash>", canonical="Pending project assignment", metadata={placeholder:true})
    ProjRepo-->>S: Project(id=P)
    Note over S: Placeholders are unique per submission; not reused
```

---

## 3. State Diagram

```mermaid
stateDiagram-v2
    [*] --> awaiting: F1 publishes ExtractionDone
    awaiting --> classifying: consumer dispatches Celery task
    classifying --> validating: confidence 0.65..0.85
    validating --> done_classified: 2nd call agrees
    validating --> not_classifiable: 2nd call disagrees
    classifying --> done_classified: confidence ≥ 0.85
    classifying --> not_classifiable: confidence < 0.65 OR LLM returns NOT_CLASSIFIABLE
    done_classified --> reclassifying: type in CVC,CVP,APV
    done_classified --> economic: type in CVP,APV,LEA,FSV,ARV
    done_classified --> elements: type otherwise (CVC, ARC, IVU)
    reclassifying --> reclassified: indicators ≥ 4
    reclassifying --> economic: indicators < 4
    reclassified --> economic
    economic --> elements: economic fields done
    elements --> project_lookup
    project_lookup --> persisted
    persisted --> published: ClassificationDone published
    published --> [*]
    not_classifiable --> [*]
```

---

## 4. Activity Diagram

```mermaid
flowchart TD
    A[Receive ExtractionDone] --> B[Call LLM classification + extraction §8.1/§8.2]
    B --> C{confidence}
    C -->|>= 0.85| D[Accept classification]
    C -->|0.65..0.85| E[Call validation §8.3]
    E --> F{agrees?}
    F -->|yes| D
    F -->|no| G[Mark NOT_CLASSIFIABLE]
    C -->|< 0.65| G
    D --> H{type in CVC,CVP,APV?}
    H -->|yes| I[Call leasing detection §8.4]
    I --> J{indicators >= 4?}
    J -->|yes| K[Reclassify to LEA]
    J -->|no| L
    H -->|no| L
    K --> L{type in CVP,APV,LEA,FSV,ARV?}
    L -->|yes| M[Call economic extraction §8.5]
    L -->|no| N[elements_detected already obtained in step B]
    M --> N
    N --> O[Normalize project name]
    O --> P{name extractable?}
    P -->|yes| Q[Upsert Project by normalized_name]
    P -->|no| R[Create placeholder unknown_<hash> Project]
    Q --> S[UPDATE contract_analysis classification block + project_id]
    R --> S
    S --> T[Publish ClassificationDone to classification.to_rubric_and_economics]
    T --> Z[End]
    G --> U[UPDATE contract_analysis contract_type=NOT_CLASSIFIABLE]
    U --> V[UPDATE contract_submission processing_status=rejected_type]
    V --> Z
```

---

## 5. Component Diagram

```mermaid
graph TD
    subgraph "External"
        OpenRouter[(OpenRouter)]
    end
    subgraph "F1 upstream"
        F1Stream[Redis Stream ingestion.to_classification]
    end
    subgraph "F2 module"
        Cons[ClassificationConsumer daemon]
        Task[Celery process_classification]
        Svc[ClassificationService]
        Norm[ProjectNameNormalizer]
        Pub[ClassificationStreamPublisher]
        Internal[InternalClassifyView]
    end
    subgraph "Repositories"
        AnaRepo[ContractAnalysisRepository]
        ProjRepo[ProjectRepository]
        JobRepo[ClassificationJobRepository]
    end
    subgraph "Stores"
        PG[(Postgres)]
        Redis[(Redis)]
    end
    subgraph "F4/F5 downstream"
        F4Stream[Redis Stream classification.to_rubric_and_economics — group rubric]
        F5Stream[Redis Stream classification.to_rubric_and_economics — group economics]
    end

    F1Stream --> Cons
    Cons --> Task
    Task --> Svc
    Internal --> Svc
    Svc --> Norm
    Svc -->|HTTPS| OpenRouter
    Svc --> AnaRepo
    Svc --> ProjRepo
    Svc --> JobRepo
    AnaRepo --> PG
    ProjRepo --> PG
    JobRepo --> PG
    Svc --> Pub
    Pub --> F4Stream
    Pub --> F5Stream
```

---

## 6. Use Case Diagram

```mermaid
graph LR
    subgraph Actors
        F1[F1 worker]
        QA[Internal operator]
    end
    subgraph "F2 Use Cases"
        UC1((Classify submission))
        UC2((Reclassify to leasing))
        UC3((Extract economic fields))
        UC4((Detect legal elements))
        UC5((Match or create Project))
        UC6((QA: classify a text directly))
    end
    F1 --> UC1
    UC1 --> UC2
    UC1 --> UC3
    UC1 --> UC4
    UC1 --> UC5
    QA --> UC6
```

---

## Notes

- The `ClassificationConsumer` is a daemon (one process) subscribed to the Redis stream with consumer group `classification`. On message receipt, it converts the envelope to JSON and dispatches a Celery task. This decouples the Redis-Streams read pattern from Celery's task model and keeps Celery's retry/back-off semantics for the LLM-heavy work.
- All four LLM calls share the same `OpenRouterClient` instance — no separate clients per step. Circuit breaker is reused from F1.
- The economic and elements extractions are sometimes performed inside the single classification call (PRD §8.1 returns `elements_detected` and there's a combined-step option). The implementation follows PRD §3 US-04/US-05 and uses one call per step for predictability and idempotency.

**End of document.**
