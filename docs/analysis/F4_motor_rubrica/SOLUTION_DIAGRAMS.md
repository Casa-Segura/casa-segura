# Solution Diagrams — F4: Rubric Engine

> Generated: 2026-05-15

---

## 1. Class Diagram

### 1.1 Domain + Application

```mermaid
classDiagram
    class Band {
        <<TextChoices>>
        GREEN
        YELLOW
        RED
        NOT_ANALYZABLE
    }
    class Severity {
        <<TextChoices>>
        CRITICAL
        RED
        YELLOW
        GREEN
        UNVERIFIABLE
    }
    class OverrideCode {
        <<TextChoices>>
        ART_1605_CC
        ART_1613_CC
        ART_1644_CC
        ART_1425_CC
        ART_3_IVU_FAMILY_HOMESTEAD
        ART_5_LPC_NON_WAIVABLE
        ART_12_LPC
        ART_13_LPC
        ART_18_LPC_BLANK_SIGNATURE
        ART_17H_LPC_ARBITRATION
        ART_58_FSV
    }
    class RubricVersion {
        <<Pydantic>>
        +str version
        +datetime released_at
        +int criteria_count
        +dict categories
        +bool is_active
    }
    class Criterion {
        <<Pydantic>>
        +str id
        +str rubric_version
        +str category
        +str title
        +str description
        +float weight_in_category
        +list~str~ applicable_types
        +list~str~ legal_anchor
        +str|None override_code
        +str evaluation_prompt
        +dict scoring_scale
        +float worst_case_when_unverifiable
    }
    class CriterionEvaluation {
        <<Pydantic>>
        +str criterion_id
        +str category
        +bool applicable
        +bool evaluated
        +bool unverifiable
        +float score
        +float weight_in_category
        +str|None override_triggered
        +str justification
        +str|None evidence_snippet
    }
    class CategoryScore {
        <<Pydantic>>
        +str category
        +str category_name
        +float weight_global
        +float weight_effective
        +float score
        +int criteria_count_total
        +int criteria_count_applicable
        +int criteria_count_unverifiable
    }
    class Finding {
        <<Pydantic>>
        +str id
        +Severity severity
        +str title
        +str description
        +str|None evidence_clause_snippet
        +list~LegalReference~ legal_basis
        +str recommendation
        +str related_criterion_id
        +str|None anchors_to_override
        +list~str~ tags
    }
    class EvaluateContractAnalysis {
        <<Command>>
        +UUID analysis_id
    }
    class AbsorbEconomicSummary {
        <<Command>>
        +UUID analysis_id
    }
    class GetCriteriaForRubricVersion {
        <<Query>>
        +str rubric_version
        +list~str~|None applicable_to_types
    }
    class rubric_handlers {
        <<handlers>>
        +evaluate_analysis(cmd) FullAnalysisResult
        +absorb_economic(cmd) None
        +list_criteria(query, repo) list~Criterion~
    }
    class RubricEvaluationService {
        -ContractAnalysisRepository analysis_repo
        -CriterionRepository criterion_repo
        -RubricVersionRepository rubric_version_repo
        -OpenRouterClient llm
        -LegalCitationService cite_service
        -CriterionEvaluator evaluator
        -ScoreCalculator score_calc
        -RubricStreamPublisher publisher
        +evaluate(analysis_id) None
        -load_inputs(analysis_id) EvaluationInputs
        -evaluate_criteria(inputs) list~CriterionEvaluation~
        -compute_scores(evals) tuple~list~CategoryScore~, float, Band~
        -emit_findings(evals, criteria) list~Finding~
        -generate_executive_summary(...) str
        -persist(analysis_id, result) None
    }
    class CriterionEvaluator {
        -OpenRouterClient llm
        +evaluate(criterion, ctx) CriterionEvaluation
        -build_prompt(criterion, ctx) ChatMessages
        -parse_response(raw) RawEvaluation
    }
    class ScoreCalculator {
        +compute_category_score(evals, criteria) CategoryScore
        +compute_total(category_scores, weights, overrides) tuple~float, Band~
        +assign_band(score, overrides_active) Band
    }
    class FindingFactory {
        -LegalCitationService cite_service
        +from_evaluation(eval, criterion, ctx) Finding
        -classify_severity(score, override) Severity
        -fetch_legal_basis(finding_description, criterion) list~LegalReference~
        -tag_when_empty(criterion, has_anchor) str
    }
    Criterion ..> OverrideCode
    CriterionEvaluation ..> OverrideCode
    Finding ..> Severity
    Finding ..> OverrideCode
    rubric_handlers ..> EvaluateContractAnalysis
    rubric_handlers ..> AbsorbEconomicSummary
    RubricEvaluationService *-- CriterionEvaluator
    RubricEvaluationService *-- ScoreCalculator
    RubricEvaluationService *-- FindingFactory
    RubricEvaluationService ..> rubric_handlers
```

### 1.2 Infrastructure

```mermaid
classDiagram
    class RubricVersionModel {
        <<Django Model>>
    }
    class CriterionModel {
        <<Django Model>>
        +TextField id
        +TextField rubric_version
        +CharField category
        +TextField title
        +TextField description
        +DecimalField weight_in_category
        +ArrayField applicable_types
        +ArrayField legal_anchor
        +CharField override_code
        +TextField evaluation_prompt
        +JSONField scoring_scale
        +DecimalField worst_case_when_unverifiable
    }
    class CriterionRepository {
        <<DjangoFullRepository>>
        +list_for_version(version, applicable_to_types) list~Criterion~
        +get_active_rubric_version() RubricVersion
    }
    class RubricVersionRepository {
        <<DjangoFullRepository>>
    }
    class ContractAnalysisRepository {
        <<DjangoFullRepository>>
        +load_full(analysis_id) FullContractAnalysisData
        +persist_evaluation(analysis_id, result) None
    }
    class OpenRouterClient {
        <<reused>>
        +chat_completion_json(model, prompt, idempotency_key) dict
    }
    class LegalCitationService {
        <<from F3>>
        +retrieve_legal_basis(text, corpus_version, top_k, threshold, prefer_anchors) list~LegalReference~
    }
    class EvaluateAnalysisTask {
        <<Celery shared_task>>
        +run(analysis_id) None
    }
    class AbsorbEconomicTask {
        <<Celery shared_task>>
        +run(analysis_id) None
    }
    class ClassificationConsumer {
        <<from F2>>
        +dispatch(envelope) None
    }
    class InternalEvaluateCriterionView {
        <<DRF APIView>>
        +post(request) Response
    }
    class InternalListCriteriaView {
        <<DRF APIView>>
        +get(request, version) Response
    }
    CriterionRepository ..> CriterionModel
    EvaluateAnalysisTask ..> RubricEvaluationService
    InternalEvaluateCriterionView ..> RubricEvaluationService
```

---

## 2. Sequence Diagrams

### 2.1 Full evaluation (chord with F5)

```mermaid
sequenceDiagram
    participant Q2 as Stream classification.to_rubric_and_economics (group rubric)
    participant C as RubricConsumer daemon
    participant F5 as F5 economic task
    participant T as EvaluateAnalysisTask
    participant S as RubricEvaluationService
    participant CR as CriterionRepository
    participant AR as ContractAnalysisRepository
    participant E as CriterionEvaluator
    participant L as OpenRouterClient
    participant Cite as LegalCitationService (F3)
    participant SC as ScoreCalculator
    participant FF as FindingFactory
    participant P as RubricStreamPublisher

    Q2-->>C: XREADGROUP envelope
    C->>T: rubric.evaluate_analysis.delay(analysis_id) (waits for F5 via chord/check)
    F5-->>AR: writes economic_summary
    F5->>T: signals "economic_done" via DB watermark or chord callback
    T->>S: evaluate(analysis_id)
    S->>AR: load_full(analysis_id) → ContractAnalysisRow + Criterion list filtered by type
    S->>CR: list_for_version(active_version, applicable_to=contract_type)
    par evaluate each criterion concurrently
        loop For each criterion (~32 calls)
            S->>E: evaluate(criterion, ctx)
            E->>L: chat_completion_json(prompt §8.1+§8.2, key=analysis:f4:crit:{id})
            L-->>E: { score, unverifiable, override_triggered, justification, evidence_snippet, recommendation }
            E->>E: if unverifiable → force score = criterion.worst_case_when_unverifiable
            E-->>S: CriterionEvaluation
        end
    end
    S->>SC: compute_category_score per category and total with overrides
    SC-->>S: scores_by_category, score_total, band
    S->>FF: emit findings (one per non-perfect criterion)
    loop per finding
        FF->>Cite: retrieve_legal_basis(description, corpus_version, prefer_anchors=criterion.legal_anchor)
        Cite-->>FF: list[LegalReference] (possibly empty)
        FF->>FF: tag market_based / unverifiable_legal if empty
        FF-->>S: Finding
    end
    S->>L: chat_completion_json(executive summary §8.3)
    L-->>S: text
    S->>AR: persist_evaluation(analysis_id, result)
    AR-->>S: ok
    S->>P: publish report_chain.dispatch(analysis_id)
    P-->>S: ok
```

### 2.2 Override path

```mermaid
sequenceDiagram
    participant S as RubricEvaluationService
    participant SC as ScoreCalculator

    S->>S: collected evaluations include one with override_triggered = "art_12_lpc"
    S->>SC: compute_total([...], overrides=["art_12_lpc"])
    SC-->>S: score_total = 0.0, band = RED
    Note over S: scores_by_category still computed honestly so the report shows the breakdown, but score_total is overridden
```

### 2.3 Unverifiable criterion

```mermaid
sequenceDiagram
    participant E as CriterionEvaluator
    participant L as OpenRouterClient

    E->>L: chat_completion_json(criterion B3 term)
    L-->>E: { unverifiable: true, justification: "term not in contract" }
    E->>E: score = criterion.worst_case_when_unverifiable (4.0)
    E-->>E: CriterionEvaluation(unverifiable=true, score=4.0, ...)
```

### 2.4 Finding without legal basis (cite-or-stay-silent)

```mermaid
sequenceDiagram
    participant FF as FindingFactory
    participant Cite as LegalCitationService

    FF->>Cite: retrieve_legal_basis(description, prefer_anchors=criterion.legal_anchor)
    Cite-->>FF: []
    FF->>FF: criterion.legal_anchor is set → tag "unverifiable_legal"
    FF-->>FF: Finding(legal_basis=[], tags=["unverifiable_legal"])
```

```mermaid
sequenceDiagram
    participant FF as FindingFactory
    participant Cite as LegalCitationService

    FF->>Cite: retrieve_legal_basis(description, prefer_anchors=[])
    Cite-->>FF: []
    FF->>FF: criterion.legal_anchor empty → tag "market_based"
    FF-->>FF: Finding(legal_basis=[], tags=["market_based"])
```

---

## 3. State Diagram — Per-criterion evaluation

```mermaid
stateDiagram-v2
    [*] --> pending: criterion in applicable list
    pending --> evaluating: worker picks
    evaluating --> retrying: LLM transient failure
    retrying --> evaluating
    evaluating --> evaluated: LLM success
    evaluating --> unverifiable_forced: LLM unverifiable=true
    evaluating --> failed: LLM permanent failure (after retry)
    failed --> unverifiable_forced: fallback to worst_case_when_unverifiable
    unverifiable_forced --> evaluated
    evaluated --> [*]
```

---

## 4. Activity Diagram

```mermaid
flowchart TD
    A[Receive analysis_id from F2 envelope + F5 done] --> B[Load analysis + criteria + economic_summary + elements_detected]
    B --> C[Filter criteria by contract_type]
    C --> D[Run per-criterion evaluations in parallel cap 8]
    D --> E{Any override triggered?}
    E -->|yes| F[Set score_total=0, band=RED]
    E -->|no| G[Compute per-category weighted average with renormalization]
    G --> H[Compute total weighted average with category renormalization]
    H --> I{score >= 8?}
    I -->|yes| J[Band=GREEN]
    I -->|no| K{score >= 5?}
    K -->|yes| L[Band=YELLOW]
    K -->|no| M[Band=RED]
    F --> N[Emit findings]
    J --> N
    L --> N
    M --> N
    N --> O{For each finding, call F3}
    O -->|results above threshold| P[Attach LegalReferences]
    O -->|empty| Q{criterion.legal_anchor empty?}
    Q -->|yes| R[Tag market_based]
    Q -->|no| S[Tag unverifiable_legal]
    P --> T[Generate executive summary via LLM]
    R --> T
    S --> T
    T --> U[Persist contract_analysis update atomically]
    U --> V[Dispatch F6 task]
    V --> [*]
```

---

## 5. Component Diagram

```mermaid
graph TD
    subgraph Inputs
        F2[F2 ClassificationDone]
        F5[F5 economic_done signal]
    end
    subgraph "F4 module"
        Consumer[RubricConsumer daemon]
        Chord[Celery chord coordinator]
        Task[EvaluateAnalysisTask]
        Svc[RubricEvaluationService]
        Eval[CriterionEvaluator]
        Score[ScoreCalculator]
        Findings[FindingFactory]
        Internal[Internal QA endpoints]
    end
    subgraph "External / shared"
        LLM[OpenRouterClient]
        F3[LegalCitationService]
    end
    subgraph "Repositories"
        CR[CriterionRepository]
        RR[RubricVersionRepository]
        AR[ContractAnalysisRepository]
    end
    subgraph "Stores"
        PG[(Postgres)]
    end
    subgraph "Downstream"
        F6Task[F6 materialize_report task]
    end

    F2 --> Consumer --> Chord --> Task --> Svc
    F5 --> Chord
    Svc --> Eval --> LLM
    Svc --> Score
    Svc --> Findings --> F3
    Svc --> CR --> PG
    Svc --> RR --> PG
    Svc --> AR --> PG
    Svc --> F6Task
    Internal --> Svc
```

---

## 6. Use Case Diagram

```mermaid
graph LR
    subgraph Actors
        F2sys[F2 worker]
        F5sys[F5 worker]
        QA[QA engineer]
        Op[Operator]
    end
    subgraph "F4 Use Cases"
        UC1((Evaluate a contract analysis))
        UC2((Force score to 0 on override))
        UC3((Renormalize weights when criteria don't apply))
        UC4((Emit findings with citations))
        UC5((Generate executive summary))
        UC6((QA: evaluate a single criterion against text))
        UC7((List criteria of a rubric version))
    end
    F2sys --> UC1
    F5sys --> UC1
    QA --> UC6
    Op --> UC7
    UC1 --> UC2
    UC1 --> UC3
    UC1 --> UC4
    UC1 --> UC5
```

---

## Notes

- The "chord with F5" can be implemented two ways: (a) a Celery `chord([f4_eval, f5_eval], report_callback)` from the F2 dispatch step, (b) a database watermark: F4's task polls `contract_analysis.economic_summary IS NOT NULL` before starting; F5 sets it. Option (b) is simpler and is what the implementation plan picks.
- `CriterionEvaluator` runs LLM calls with concurrency bounded by `LLM_RUBRIC_CONCURRENCY`; uses `asyncio.Semaphore(8)`.
- `FindingFactory.from_evaluation` may produce zero findings only when `eval.score == 10`. Otherwise exactly one finding per evaluation.
- The `executive_summary` step is the only place F4 invokes the LLM after all criteria are evaluated; the prompt receives only aggregates (band, score, counts), not the contract text — keeps the call cheap and predictable.

**End of document.**
