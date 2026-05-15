# Feature Overview — F6: Report Generation

> Generated: 2026-05-15
> Stack: Django 5.2 LTS + Jinja2 + WeasyPrint
> Depends: F3 (corpus for "see verbatim"), F4 (analysis), F5 (economic), F8 (schema)
> Blocks: F7 (delivery)

---

## Executive Summary

F6 turns the structured analysis stored in `ContractAnalysis` (and joined with `Project`, `LegalChunk`, `RubricVersion`) into a **responsive HTML report** with 8 sections, and renders that HTML to a **downloadable PDF** via WeasyPrint. The report is never persisted: each access regenerates it from the analysis row. This honors the privacy contract (no static artifacts) and simplifies retention.

F6 is **read-only** with respect to business data. It only writes one optional observability row (`ReportGenerationLog`). It calls F3 only when the user clicks "See verbatim text" (fetched on-demand). It calls the LLM only once per report — to generate the "Lleva al abogado" actionable block.

The report uses versioned templates (`v1`), Spanish "tú", color-coded bands (green/yellow/red), inline SVG bar charts for benchmark comparisons, and the disclaimer "Esto no es asesoría legal" in header, footer, and before critical findings. The Art. 1686 CC warning is rendered in purchase reports per the `art_1686_warning_mode` policy (default `always`).

---

## Key Concepts

| Term | Plain-language definition |
|---|---|
| **HTML report** | Responsive, self-contained HTML 200 KB-ish, no external assets |
| **PDF report** | WeasyPrint conversion, < 1 MB, watermarked |
| **Template version** | Versioning the visual format so old analyses regenerate identically |
| **Anonymized template** | Reduced version for analyses past 90 days |
| **"Lleva al abogado" block** | LLM-generated 3-5 conversation points; only block that uses LLM |
| **`X-Robots-Tag: noindex`** | The HTML must not be indexed by search engines |
| **`Cache-Control: no-store`** | The HTML must not be cached by CDNs |
| **`text_verbatim` fetch** | On user expand-action, F6 calls F3 to load the verbatim article |

---

## How It Works (Step by Step)

1. **F6 receives** a Celery task `reports.materialize_report(analysis_id)` chained after F4. F6 is also invoked synchronously by F7 when the user clicks the public link.
2. **F6 loads** `ContractAnalysis` joined with `Project`, `RubricVersion`. Determines branch:
   - If `anonymized_at IS NULL` → render full template
   - Else → render anonymized template
3. **F6 generates** the LLM "Lleva al abogado" block via OpenRouter (prompt §8.1 of PRD_F6, ≤ 5 items, deterministic fallback on failure).
4. **F6 composes** the eight sections (header, verdict, economic, categories, findings, legal_refs, actions, footer) via Jinja2.
5. **F6 returns** HTML (text) or PDF (bytes). For the public link served by F7, only HTML; for email, PDF (F7 calls `generate_report_pdf`).
6. **F6 logs** one row in `ReportGenerationLog` (optional, 30-day TTL).

---

## Business Rules

- **BR-F6-01:** HTML/PDF never persisted to disk or DB.
- **BR-F6-02:** Disclaimer in header, footer, and before critical findings; invariant.
- **BR-F6-03:** Use the versions stored on `ContractAnalysis`, not current.
- **BR-F6-04:** Spanish "tú", no localization.
- **BR-F6-05:** Never reproduce full contract text; only the snippet inside findings.
- **BR-F6-06:** No external logos in the report.
- **BR-F6-07:** Anonymized reports show a clear notice.
- **BR-F6-08:** Art. 1686 CC warning configurable: `always | when_red | never` (default `always`).
- **BR-F6-09:** Project-name note ("extraído del contrato, no verificado") always rendered.
- **BR-F6-10:** Project context: "Casa Segura has analyzed N contracts of this project; avg X.X" when N ≥ 2.
- **BR-F6-11:** Footer offers `errores@casasegura.sv` reporting link.
- **BR-F6-12:** Footer declares `rubric_version`, `corpus_version`, `benchmark_version`, and an analysis hash.
- **BR-F6-13:** Only expand/collapse JS, no external scripts.
- **BR-F6-14:** No web fonts, no remote images, no CDN — fully offline-renderable.

---

## What Changes in the System

- New Jinja2 templates under `reports/templates/report/v1/`
- New management command (none required); F6 is invoked programmatically
- Optional table `report_generation_log` (30-day TTL; cleaned by F8 cron)
- Celery task `reports.materialize_report` (a no-op in MVP — F7 calls F6 synchronously when serving; the task placeholder is there for future async pre-warming)
- Internal endpoints `GET /v1/internal/reports/{id}/html`, `GET /v1/internal/reports/{id}/pdf`, `POST /v1/internal/reports/preview`

---

## What This Feature Does NOT Do

- Persist the report (privacy contract)
- Serve the report via public link (F7)
- Send via email/WhatsApp (F7)
- Internationalize beyond Spanish
- Customize per project/brand (no white-labeling)
- Export JSON/DOCX (Spanish HTML + PDF only)

---

## Audit and Compliance

- `ReportGenerationLog` records generation events: `analysis_id`, `format`, `status`, `bytes_generated`, `generation_time_ms`.
- No HTML/PDF persisted; logs do not include the rendered content.
- The "Lleva al abogado" LLM call is logged with tokens/cost.

---

## Assumptions Made

- `art_1686_warning_mode = "always"` (default per `_shared/GLOBAL_ASSUMPTIONS.md` §10).
- LLM provides the "Lleva al abogado" block; deterministic fallback uses pre-written templates when LLM fails.
- HTML template `v1` is the only template at MVP; deployments can later add `v2` with backward compatibility.
- PDF page size: Letter (PRD §6.5 default).
- PDF margin: 1.5 cm.
- Max findings before collapse: 25 (configurable). F4 emits all; F6 caps the visible critical-and-red list and groups the rest under "Otros puntos".

---

**End of document.**
