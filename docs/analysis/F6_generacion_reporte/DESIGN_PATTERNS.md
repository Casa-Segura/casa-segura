# Design Patterns — F6: Report Generation

> Generated: 2026-05-15

---

## Patterns Applied

### Versioned templates

**Why it fits:** Visual format changes over time. To honor reproducibility (PRD BR-03), each `ContractAnalysis` records which template version it was rendered with (`ContractAnalysis.report_template_version`, default to current). F6 keeps `v1`, `v2`, ... directories in templates.

**Implementation:** `templates/report/{v1,v2}/full.html.j2`; `ReportTemplateRenderer.render(name, ctx)` joins `template_version` + name.

---

### Read-only Service

**Why it fits:** F6 must not change business state. The only writes are `ReportGenerationLog` (observability) and nothing else. The contract with F4/F5 is one-way: `ReportService` reads only.

---

### Template Method (Jinja2)

**Why it fits:** Sections are reusable across full and anonymized templates. The eight section partials (`_header.html.j2`, `_verdict.html.j2`, etc.) are included by both top-level templates with context flags toggling sub-blocks.

---

### Compose-then-render

**Why it fits:** Building the `ReportBuildContext` (one Pydantic object) before rendering simplifies tests: assertions are over the context, not the HTML string.

---

### Fallback (LLM → deterministic)

**Why it fits:** The LLM call for "Lleva al abogado" can fail. The report must still render. A deterministic fallback per band ensures every report has the block.

**Implementation:** `TakeToLawyerLlm.fallback(band)` returns a static list per band.

---

### Capability token-bound rendering

**Why it fits:** The HTML/PDF includes a hash of the analysis (`ContractAnalysis.id + rubric_version + corpus_version + benchmark_version + rendered_at`). The footer displays "Hash del análisis: ABC123…" so a recipient can verify the doc was produced by Casa Segura (not modified). The hash is **not** for authentication; only integrity (the user can paste it into an upcoming `/v1/internal/verify-report-hash` for QA).

---

### Streaming PDF generation

**Why it fits:** WeasyPrint can be slow on large reports. For PDFs above a size threshold, F6 can stream the response to F7 without buffering all bytes. At MVP, PDFs are < 1 MB, so the whole bytes are returned synchronously; the streaming path is wired but not engaged.

---

## Patterns Considered and Rejected

### Persist generated PDFs

Tempting: cache PDFs in S3 with short TTL. Rejected because: violates BR-F6-01 (no persistence); the privacy story is muddled if a PDF exists outside the database for any time.

### Server-side React rendering

A heavier templating engine. Rejected because: Jinja2 is sufficient for a static HTML report; no client-side state; bundle size is zero.

### Email-based report (HTML in body)

Tempting: send the full HTML in the email body. Rejected because: mail clients render HTML inconsistently; attached PDF + link to web is the more reliable UX (and matches PRD §6.2 / §6.3).

### White-labeling per project/developer

PRD §10 Q-3. Rejected at MVP — opens template complexity without product clarity.

### Signing the PDF cryptographically

PRD §10 Q-6. Rejected at MVP — gives the impression of legal advice (against disclaimer); cost of key management without proportional benefit.

---

**End of document.**
