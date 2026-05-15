# Solution Diagrams — F6: Report Generation

> Generated: 2026-05-15

---

## 1. Class Diagram

### 1.1 Domain + Application

```mermaid
classDiagram
    class ReportBuildContext { <<Pydantic>> }
    class GenerateReportHtml {
        <<Command>>
        +UUID analysis_id
        +str template_version
    }
    class GenerateReportPdf {
        <<Command>>
        +UUID analysis_id
        +str template_version
    }
    class FetchVerbatim {
        <<Query>>
        +str law_id
        +str anchor
        +str corpus_version
    }
    class LogReportGeneration {
        <<Command>>
        +ReportGenerationLog entry
    }
    class ReportService {
        -ContractAnalysisRepository analysis_repo
        -ProjectRepository project_repo
        -RubricVersionRepository rubric_repo
        -LegalCitationService cite_service
        -ReportTemplateRenderer renderer
        -ReportPdfRenderer pdf_renderer
        -TakeToLawyerLlm lawyer_llm
        -ReportGenerationLogRepository log_repo
        +generate_html(analysis_id, template_version) tuple~str, ReportBuildContext~
        +generate_pdf(analysis_id, template_version) bytes
        +fetch_verbatim(law_id, anchor, corpus_version) LegalReference|None
        -build_context(analysis_id) ReportBuildContext
        -render_html(ctx) str
        -render_pdf(html) bytes
    }
    class ReportTemplateRenderer {
        -Environment jinja_env
        +render(template_name, ctx) str
    }
    class ReportPdfRenderer {
        +to_pdf(html_str) bytes
    }
    class TakeToLawyerLlm {
        -OpenRouterClient llm
        +generate(ctx) list~str~
        -fallback(band) list~str~
    }
    class ReportFinder {
        +findings_for_render(findings, cap) tuple~visible, collapsed~
    }
    ReportService *-- ReportTemplateRenderer
    ReportService *-- ReportPdfRenderer
    ReportService *-- TakeToLawyerLlm
    ReportService *-- ReportFinder
```

### 1.2 Infrastructure

```mermaid
classDiagram
    class ReportGenerationLogModel { <<Django Model>> }
    class ReportGenerationLogRepository { <<DjangoFullRepository>> }
    class ReportTemplateRenderer {
        <<Jinja2 wrapper>>
    }
    class ReportPdfRenderer {
        <<WeasyPrint wrapper>>
    }
    class TakeToLawyerLlm {
        <<OpenRouter wrapper>>
    }
    class InternalHtmlView {
        <<DRF APIView>>
        +get(request, analysis_id) Response
    }
    class InternalPdfView {
        <<DRF APIView>>
        +get(request, analysis_id) HttpResponse
    }
    class InternalPreviewView {
        <<DRF APIView>>
        +post(request) Response
    }
    class MaterializeReportTask { <<Celery shared_task>> }
    ReportGenerationLogRepository ..> ReportGenerationLogModel
    MaterializeReportTask ..> ReportService
    InternalHtmlView ..> ReportService
    InternalPdfView ..> ReportService
```

---

## 2. Sequence Diagrams

### 2.1 Serve HTML via public link (called from F7)

```mermaid
sequenceDiagram
    actor U as User (browser)
    participant F7 as PublicLinkView (F7)
    participant Svc as ReportService
    participant AR as ContractAnalysisRepository
    participant PR as ProjectRepository
    participant RR as RubricVersionRepository
    participant LL as TakeToLawyerLlm
    participant R as ReportTemplateRenderer
    participant Log as ReportGenerationLogRepository

    U->>F7: GET /r/CS-2026-A1B2C3
    F7->>Svc: generate_html(analysis_id)
    Svc->>AR: load_full(analysis_id)
    AR-->>Svc: ContractAnalysis joined
    alt anonymized
        Svc->>R: render template_anonymized.html.j2
    else not anonymized
        Svc->>PR: get(analysis.project_id)
        Svc->>RR: get(analysis.rubric_version)
        Svc->>LL: generate(ctx) (LLM call)
        LL-->>Svc: list of 3-5 items
        Svc->>R: render full.html.j2
    end
    R-->>Svc: html string
    Svc->>Log: log(report_generation_log success, ms, bytes)
    Svc-->>F7: html
    F7-->>U: 200 text/html with X-Robots-Tag, Cache-Control: no-store
```

### 2.2 Generate PDF for email (called from F7)

```mermaid
sequenceDiagram
    participant F7 as EmailDeliveryTask
    participant Svc as ReportService
    participant R as ReportTemplateRenderer
    participant PR as ReportPdfRenderer

    F7->>Svc: generate_pdf(analysis_id)
    Svc->>Svc: build_context + render html (same as 2.1)
    Svc->>PR: to_pdf(html)
    PR->>PR: WeasyPrint.HTML(string=html).write_pdf()
    PR-->>Svc: bytes
    Svc-->>F7: bytes
```

### 2.3 See verbatim text

```mermaid
sequenceDiagram
    actor U as User (browser)
    participant FE as Report HTML JS
    participant Svc as ReportService
    participant F3 as LegalCitationService

    U->>FE: click "Ver texto completo"
    FE->>Svc: GET /r/{short_id}/legal/{law_id}/{anchor}
    Svc->>F3: get_chunk_by_anchor(law_id, anchor, analysis.corpus_version)
    F3-->>Svc: LegalReference
    Svc-->>FE: JSON with text_verbatim
```

### 2.4 LLM failure → deterministic fallback

```mermaid
sequenceDiagram
    participant Svc as ReportService
    participant LL as TakeToLawyerLlm

    Svc->>LL: generate(ctx)
    LL->>LL: OpenRouter call fails twice
    LL-->>LL: fallback(band)
    LL-->>Svc: ["Pregúntale a tu abogado si ...", "Confirma si ..."]
```

---

## 3. State Diagram — Report generation per request

```mermaid
stateDiagram-v2
    [*] --> loading: receive analysis_id
    loading --> branching: data loaded
    branching --> rendering_anonymized: anonymized_at not null
    branching --> rendering_full: not anonymized
    rendering_full --> calling_llm: take_to_lawyer block
    calling_llm --> templating: LLM ok or fallback
    rendering_anonymized --> templating
    templating --> html_ready
    html_ready --> pdf_rendering: if PDF requested
    html_ready --> [*]: if HTML only
    pdf_rendering --> pdf_ready
    pdf_ready --> [*]
```

---

## 4. Activity Diagram

```mermaid
flowchart TD
    A[Request HTML or PDF for analysis_id] --> B[Load ContractAnalysis joined data]
    B --> C{anonymized?}
    C -->|yes| D[Render template_anonymized]
    C -->|no| E[Load Project, RubricVersion]
    E --> F[Decide which findings to cap to 25 visible]
    F --> G[Generate take-to-lawyer items via LLM with fallback]
    G --> H[Render template_v1 full]
    D --> I[HTML ready]
    H --> I
    I --> J{Format?}
    J -->|html| K[Return string]
    J -->|pdf| L[WeasyPrint.write_pdf]
    L --> M[Return bytes]
    K --> N[Log success in report_generation_log]
    M --> N
    N --> Z[End]
```

---

## 5. Component Diagram

```mermaid
graph TD
    F7Public[F7 public link view]
    F7Email[F7 email task]
    Svc[ReportService]
    AR[ContractAnalysisRepository]
    PR[ProjectRepository]
    RR[RubricVersionRepository]
    F3[LegalCitationService]
    LL[TakeToLawyerLlm]
    OR[OpenRouter]
    R[Jinja2 templates v1]
    PDF[WeasyPrint]
    Log[ReportGenerationLogRepository]
    PG[(Postgres)]
    Internal[Internal QA endpoints]

    F7Public --> Svc
    F7Email --> Svc
    Internal --> Svc
    Svc --> AR --> PG
    Svc --> PR --> PG
    Svc --> RR --> PG
    Svc --> F3
    Svc --> LL --> OR
    Svc --> R
    Svc --> PDF
    Svc --> Log --> PG
```

---

## 6. Use Case Diagram

```mermaid
graph LR
    User[Anonymous user]
    F7sys[F7 delivery]
    QA[QA engineer]

    User --> UC1((View report via public link))
    User --> UC2((See verbatim of a cited article))
    F7sys --> UC3((Render PDF for email))
    F7sys --> UC4((Render HTML for web link))
    QA --> UC5((Preview a report with mock data))
```

**End of document.**
