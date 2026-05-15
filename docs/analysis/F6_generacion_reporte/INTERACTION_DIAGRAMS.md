# Interaction Diagrams — F6: Report Generation

> Generated: 2026-05-15

---

## Component Overview

```mermaid
graph TD
    F7Public[F7 public link]
    F7Email[F7 email task]
    Svc[ReportService]
    LLM[TakeToLawyerLlm]
    OR[OpenRouter]
    F3[F3 LegalCitationService]
    Jinja[Jinja2 v1 templates]
    Weasy[WeasyPrint]
    PG[(Postgres)]

    F7Public --> Svc
    F7Email --> Svc
    Svc --> LLM --> OR
    Svc --> F3
    Svc --> Jinja
    Svc --> Weasy
    Svc --> PG
```

---

## Flow: US-01 Compose full HTML

```mermaid
sequenceDiagram
    participant F7 as F7 PublicLinkView
    participant Svc as ReportService
    participant AR as ContractAnalysisRepository
    participant LL as TakeToLawyerLlm
    participant J as Jinja2 env
    participant Log as ReportGenerationLogRepository

    F7->>Svc: generate_html(analysis_id, template_version="v1")
    Svc->>AR: load_full(analysis_id) returns analysis joined with project, rubric_version, etc.
    Svc->>Svc: detect anonymized? no → full path
    Svc->>LL: generate(ctx) (LLM call for "take to lawyer" block)
    LL-->>Svc: 4 items
    Svc->>J: render("v1/full.html.j2", ctx)
    J-->>Svc: html string
    Svc->>Log: write log row (success, ms, bytes)
    Svc-->>F7: html
```

---

## Flow: US-02 Header with disclaimer

(Pure templating; nothing remote.)

---

## Flow: US-03 Verdict section

(Includes large score, band-coloured div, executive summary text from `contract_analysis.executive_summary`. Override box rendered conditionally when `override_triggered` is non-empty.)

---

## Flow: US-04 Economic visualization

```mermaid
sequenceDiagram
    participant J as Jinja2
    participant Svc as ReportService

    Svc->>J: data ctx.analysis.economic_summary.benchmark_comparisons
    J->>J: for each comparison render inline SVG horizontal bar
    Note over J: contract bar width = contract_value/scale_max; benchmark bar width = benchmark_value/scale_max
    J->>J: render overcost block if economic_summary.overcost is not null
    J->>J: render Art. 1686 CC warning if mode applies
```

---

## Flow: US-05 Categories breakdown

```mermaid
sequenceDiagram
    participant J as Jinja2
    participant Svc as ReportService

    Svc->>J: for category in ctx.analysis.scores_by_category, sorted by global weight desc
    J->>J: render collapsed block; expand reveals criterion_evaluations filtered by category
```

---

## Flow: US-06 Findings list

```mermaid
sequenceDiagram
    participant J as Jinja2
    participant Svc as ReportService
    participant F3 as LegalCitationService

    Note over Svc: F4 already stored legal_basis inside each finding; F6 does not call F3 here
    Svc->>J: pass findings sorted by severity, weight desc
    J->>J: if any critical, render disclaimer again before list
    J->>J: render each finding with severity icon, evidence_clause_snippet, legal_basis list, recommendation
    J->>J: cap visible at 25, collapse the rest under "Otros puntos"
```

---

## Flow: US-07 Suggested actions

```mermaid
sequenceDiagram
    participant LL as TakeToLawyerLlm
    participant Svc as ReportService
    participant OR as OpenRouter

    Svc->>LL: generate(ctx) — includes critical and red findings only
    LL->>OR: chat_completion_json(prompt §8.1, idempotency_key=analysis:f6:lawyer)
    OR-->>LL: { items: ["...", "...", "..."] }
    LL-->>Svc: items
    Note over Svc: "Antes de firmar" block built from critical+red recommendations
    Note over Svc: "Documentos que debes exigir" block built from category D + elements_detected
```

---

## Flow: US-08 Anonymized report

```mermaid
sequenceDiagram
    participant Svc as ReportService
    participant J as Jinja2

    Svc->>Svc: branch on analysis.anonymized_at IS NOT NULL
    Svc->>J: render "v1/anonymized.html.j2"
    Note over J: only band, score, executive_summary, severity counts, bucket-form economic
```

---

## Flow: US-09 PDF rendering

```mermaid
sequenceDiagram
    participant Svc as ReportService
    participant Weasy as WeasyPrint

    Svc->>Svc: render html as above
    Svc->>Weasy: HTML(string=html, base_url=settings.STATIC_ROOT).write_pdf(stylesheets=[print_css])
    Weasy-->>Svc: bytes
```

---

## Class Diagram

```mermaid
classDiagram
    class ReportService
    class TakeToLawyerLlm
    class ReportTemplateRenderer
    class ReportPdfRenderer
    class ReportFinder
    class ContractAnalysisRepository
    class ProjectRepository
    class RubricVersionRepository
    class ReportGenerationLogRepository
    class LegalCitationService
    class MaterializeReportTask
    class InternalHtmlView
    class InternalPdfView
    class InternalPreviewView

    ReportService *-- TakeToLawyerLlm
    ReportService *-- ReportTemplateRenderer
    ReportService *-- ReportPdfRenderer
    ReportService *-- ReportFinder
    ReportService o-- ContractAnalysisRepository
    ReportService o-- ProjectRepository
    ReportService o-- RubricVersionRepository
    ReportService o-- LegalCitationService
    ReportService o-- ReportGenerationLogRepository
    MaterializeReportTask ..> ReportService
    InternalHtmlView ..> ReportService
    InternalPdfView ..> ReportService
```

**End of document.**
