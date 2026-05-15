# Implementation Plan — F6: Report Generation

> Generated: 2026-05-15
> Stack: Django 5.2 LTS + Jinja2 + WeasyPrint + Celery
> Module: `reports/`
> Depends: F3 (corpus), F4 (analysis), F5 (economic summary), F8 (schema).

---

## Directory Structure

```
reports/
├── domain/
│   ├── entities.py           # ReportBuildContext, ReportGenerationLog, ContractAnalysisView (full read DTO)
│   ├── enums.py              # ReportFormat, ReportStatus
│   └── exceptions.py
├── application/
│   ├── commands.py           # GenerateReportHtml, GenerateReportPdf, LogReportGeneration
│   ├── queries.py            # FetchVerbatim, LoadFullAnalysisForReport
│   ├── handlers/
│   │   └── report_handlers.py
│   └── services/
│       ├── report_service.py
│       ├── take_to_lawyer_llm.py
│       └── report_finder.py
├── infrastructure/
│   ├── django/
│   │   ├── apps.py
│   │   ├── models.py         # ReportGenerationLogModel
│   │   ├── repositories.py
│   │   ├── serializers.py
│   │   ├── views.py          # InternalHtmlView, InternalPdfView, InternalPreviewView, SeeVerbatimView
│   │   ├── urls.py
│   │   └── migrations/0001_initial.py
│   ├── celery/
│   │   └── report_tasks.py   # @shared_task materialize_report (no-op MVP, future pre-warm)
│   ├── rendering/
│   │   ├── jinja_env.py      # Jinja2 environment factory
│   │   └── pdf_renderer.py   # WeasyPrint wrapper
│   ├── llm/
│   │   └── lawyer_prompt.py  # §8.1 prompt verbatim
│   └── templates/
│       └── report/
│           └── v1/
│               ├── full.html.j2
│               ├── anonymized.html.j2
│               ├── _header.html.j2
│               ├── _verdict.html.j2
│               ├── _economic.html.j2
│               ├── _categories.html.j2
│               ├── _findings.html.j2
│               ├── _legal_refs.html.j2
│               ├── _actions.html.j2
│               ├── _footer.html.j2
│               └── style.css
```

---

## App Configuration

```python
# reports/infrastructure/django/apps.py
from django.apps import AppConfig

class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "reports.infrastructure.django"
    label = "reports"
    verbose_name = "Casa Segura — Report Generation"
```

---

## Domain Entities (Pydantic)

```python
# reports/domain/entities.py
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict


class ReportGenerationLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID | None = None
    analysis_id: UUID
    public_short_id: str
    format: Literal["html","pdf"]
    requested_at: datetime
    generation_time_ms: int | None = None
    status: Literal["success","failed"]
    error_code: str | None = None
    bytes_generated: int | None = None
    expires_at: datetime


class ReportBuildContext(BaseModel):
    analysis_id: UUID
    public_short_id: str
    project_canonical_name: str
    project_normalized_name: str
    project_total_analyses: int
    project_avg_score: float | None
    contract_type: str
    contract_type_declared: str | None
    contract_type_reclassified: bool
    reclassification_reason: str | None
    score_total: float
    band: str
    override_triggered: list[str]
    scores_by_category: list[dict]
    criterion_evaluations: list[dict]
    findings_visible: list[dict]
    findings_collapsed: list[dict]
    findings_count: int
    critical_findings_count: int
    unverifiable_count: int
    executive_summary: str
    economic_summary: dict | None
    take_to_lawyer_items: list[str]
    documents_to_demand: list[str]
    before_signing_items: list[str]
    rubric_version: str
    corpus_version: str
    benchmark_version: str
    template_version: str = "v1"
    art_1686_warning_mode: Literal["always","when_red","never"] = "always"
    show_art_1686: bool = True
    is_anonymized: bool = False
    anonymized_at: datetime | None = None
    rendered_at: datetime
    analysis_hash: str
```

## Enumerations

```python
# reports/domain/enums.py
from django.db import models

class ReportFormat(models.TextChoices):
    HTML = "html"
    PDF = "pdf"

class ReportStatus(models.TextChoices):
    SUCCESS = "success"
    FAILED = "failed"
```

## Commands and Queries

```python
# reports/application/commands.py
from uuid import UUID
from pydantic import BaseModel
from reports.domain.entities import ReportGenerationLog


class GenerateReportHtml(BaseModel):
    analysis_id: UUID
    template_version: str = "v1"

class GenerateReportPdf(BaseModel):
    analysis_id: UUID
    template_version: str = "v1"

class LogReportGeneration(BaseModel):
    entry: ReportGenerationLog
```

```python
# reports/application/queries.py
from shared.domain.entities.cqrs import BaseGetAttributes, Query


class FetchVerbatim(BaseGetAttributes, Query):
    law_id: str
    anchor: str
    corpus_version: str

class LoadFullAnalysisForReport(BaseGetAttributes, Query):
    analysis_id: str
```

## New Dependencies

| Package | Version | Reason |
|---|---|---|
| `Jinja2` | ≥ 3.1 | Templating |
| `weasyprint` | ≥ 60 | HTML→PDF |
| `pydyf` | ≥ 0.10 | WeasyPrint dep |
| `cssselect2` | latest | CSS for WeasyPrint |
| `tinycss2` | latest | idem |
| `cairocffi` | latest | rendering (PNG) |

OS deps for WeasyPrint: `libcairo2`, `libpango-1.0-0`, `libpangocairo-1.0-0`, `libgdk-pixbuf2.0-0` — installed in the API + worker images.

---

## Story: US-01 Compose HTML

`ReportService.generate_html(analysis_id, template_version)` performs the entire build. Returns `(html_str, ctx)`.

## Story: US-02 Header
Section partial `_header.html.j2`. Disclaimer styled `background: #FEF3C7; border-left: 4px solid #F59E0B`.

## Story: US-03 Verdict
`_verdict.html.j2`. Color tokens:
- Green `#10B981`
- Yellow `#F59E0B`
- Red `#EF4444`

Override box conditional on `override_triggered`.

## Story: US-04 Economic visualization
`_economic.html.j2`. Inline SVG for benchmark comparisons. Art. 1686 CC warning conditional on `art_1686_warning_mode` + `band` + `contract_type`.

## Story: US-05 Categories breakdown
`_categories.html.j2`. Expand/collapse blocks per category.

## Story: US-06 Findings
`_findings.html.j2`. The `ReportFinder.findings_for_render(findings, cap=25)` decides which findings render expanded and which collapsed under "Otros puntos".

## Story: US-07 Suggested actions
`_actions.html.j2`. Three blocks:
1. Before signing — built by `ctx.before_signing_items` from critical+red finding recommendations.
2. Lleva al abogado — `ctx.take_to_lawyer_items` from LLM.
3. Documents to demand — `ctx.documents_to_demand` from category D + `elements_detected`.

## Story: US-08 Anonymized template
`anonymized.html.j2`. Shows only band, score, executive_summary, severity counts, bucketed economic summary.

## Story: US-09 PDF rendering
`ReportPdfRenderer.to_pdf(html_str)` wraps WeasyPrint. Watermark via CSS `@page` background.

## Story: US-10 Versioning
`template_version` defaults to `v1`. Stored on `ContractAnalysis.report_template_version` (optional column from F8). Footer declares all three versions + hash.

---

## Part 2 — Staged Execution Plan

### Codebase Alignment Rules

- Django 5.2 LTS + DRF for internal endpoints only
- `ReportGenerationLogModel` declared by F6 (its own migrations)
- Celery task `reports.materialize_report` (placeholder MVP; F7 calls F6 synchronously today)
- LLM call only for the lawyer block
- All templates under `reports/infrastructure/templates/report/v1/`
- No external assets; `<base href>` not used

### Stage Overview

| # | Stage | Deliverable |
|---|---|---|
| 1 | Domain entities + enums + exceptions | Pydantic + TextChoices |
| 2 | Commands + queries | CQRS |
| 3 | Handlers | Plain functions |
| 4 | Services | ReportService, ReportFinder |
| 5 | Templates v1 + style.css | Jinja2 templates |
| 6 | PDF rendering | WeasyPrint wrapper |
| 7 | LLM lawyer block + fallback | TakeToLawyerLlm |
| 8 | Django model + repository | ReportGenerationLogModel + repository |
| 9 | DRF views + URLs | InternalHtmlView, InternalPdfView, InternalPreviewView, SeeVerbatimView (served at `/r/{short_id}/legal/{law_id}/{anchor}`) |
| 10 | Celery task placeholder | reports.materialize_report (no-op MVP) |
| 11 | Tests | unit + golden HTML tests + WeasyPrint smoke |
| 12 | Observability | Prometheus metrics |

### Stage 5: Templates outline

Full template (`v1/full.html.j2`):

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>Análisis de Contrato Casa Segura — {{ public_short_id }}</title>
    <style>{% include "report/v1/style.css" %}</style>
</head>
<body>
    {% include "report/v1/_header.html.j2" %}
    {% include "report/v1/_verdict.html.j2" %}
    {% if economic_summary %}{% include "report/v1/_economic.html.j2" %}{% endif %}
    {% include "report/v1/_categories.html.j2" %}
    {% include "report/v1/_findings.html.j2" %}
    {% include "report/v1/_legal_refs.html.j2" %}
    {% include "report/v1/_actions.html.j2" %}
    {% include "report/v1/_footer.html.j2" %}
    <script>
        document.querySelectorAll('.cs-collapsible').forEach(el => {
            el.addEventListener('click', () => el.classList.toggle('open'));
        });
    </script>
</body>
</html>
```

### Stage 8: Django model

```python
# reports/infrastructure/django/models.py
import uuid
from django.db import models
from reports.domain.enums import ReportFormat, ReportStatus


class ReportGenerationLogModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    analysis_id = models.UUIDField(db_index=True, help_text="ContractAnalysis id.")
    public_short_id = models.TextField(db_index=True, help_text="Short id for correlation.")
    format = models.CharField(max_length=8, choices=ReportFormat.choices, help_text="html or pdf.")
    requested_at = models.DateTimeField(auto_now_add=True, help_text="Generation start time.")
    generation_time_ms = models.IntegerField(null=True, help_text="Elapsed ms.")
    status = models.CharField(max_length=16, choices=ReportStatus.choices, help_text="Outcome.")
    error_code = models.CharField(max_length=64, null=True, blank=True, help_text="If failed.")
    bytes_generated = models.IntegerField(null=True, help_text="Output size.")
    expires_at = models.DateTimeField(db_index=True, help_text="Cleanup trigger (F8 cron).")

    class Meta:
        db_table = "report_generation_log"

    def __str__(self) -> str:
        return f"ReportGenerationLog {self.id} ({self.format}, {self.status})"
```

### Stage 9 — Views and URLs

```python
# reports/infrastructure/django/views.py
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from shared.infrastructure.django.permissions import HasInternalAuthHeader, IsCapabilityHolder
from reports.application.services.report_service import ReportService

class InternalHtmlView(APIView):
    permission_classes = [HasInternalAuthHeader]
    report_service = ReportService(...)

    def get(self, request, analysis_id: str):
        html, _ctx = self.report_service.generate_html(UUID(analysis_id))
        return HttpResponse(html, content_type="text/html; charset=utf-8")

class InternalPdfView(APIView):
    permission_classes = [HasInternalAuthHeader]
    report_service = ReportService(...)

    def get(self, request, analysis_id: str):
        pdf_bytes = self.report_service.generate_pdf(UUID(analysis_id))
        return HttpResponse(pdf_bytes, content_type="application/pdf")

class SeeVerbatimView(APIView):
    """Public-facing helper for the report's expand-verbatim feature.
    Permission: the request only succeeds if the short id in the URL exists and has a valid (not expired) link.
    """
    permission_classes = []  # custom logic below
    report_service = ReportService(...)

    def get(self, request, short_id: str, law_id: str, anchor: str):
        # resolve analysis by short_id, check link expiration; if ok call report_service.fetch_verbatim
        ...
```

### Stage 12 — Metrics

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `f6_render_latency_seconds` | Histogram | `format` | P50/P95 |
| `f6_render_outcome_total` | Counter | `format`, `outcome` | Funnel |
| `f6_pdf_size_bytes` | Histogram | — | PDF size distribution |
| `f6_lawyer_llm_outcome_total` | Counter | `outcome` (success/fallback) | LLM reliability |
| `f6_verbatim_lookups_total` | Counter | — | User engagement |

---

## Configuration matrix

| Variable | Default | Purpose |
|---|---|---|
| `REPORT_TEMPLATE_VERSION` | `v1` | Default template |
| `REPORT_PDF_PAGE_SIZE` | `Letter` | — |
| `REPORT_PDF_MARGIN_CM` | `1.5` | — |
| `REPORT_INCLUDE_ART_1686_WARNING` | `always` | Policy |
| `REPORT_MAX_FINDINGS_BEFORE_COLLAPSE` | 25 | UI cap |
| `LLM_LAWYER_MODEL` | `anthropic/claude-sonnet-4` | LLM model |
| `LLM_LAWYER_TIMEOUT_SECONDS` | 30 | — |

---

**End of document.**
