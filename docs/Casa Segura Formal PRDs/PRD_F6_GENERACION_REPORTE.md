# PRD: F6 — Report Generation

**Version:** 1.0
**Status:** Approved for development
**Author:** Product Team
**Date:** 2026-05-10
**Depends on:** F3 (Corpus/RAG for legal citations), F4 (Rubric Engine), F5 (Economic Analysis), F8 (database schema base)
**Blocks:** F7 (Multi-Channel Delivery)

---

## 1. Problem Statement

The complete contract analysis lives in `ContractAnalysis` as structured data (scores, findings, economic comparisons, legal citations). The user, however, needs to see that as a legible, navigable, shareable document. F6 is the layer that takes the structured analysis and converts it into a responsive HTML report that renders correctly on a mid-range Android phone, and optionally into a downloadable PDF for email or personal archive.

The feature has four challenges. First, the report must be dense yet legible: eight sections with clear hierarchy, distinct visual formats per finding severity, and economic comparisons that need visualization. Second, the report is not persisted: each time the user accesses the link, it is regenerated from the `ContractAnalysis` row. This is a privacy constraint and simplifies retention. Third, the report must be reproducible: if the legal corpus or rubric changes, regenerated reports must use the version the original analysis was created with. Fourth, the PDF must preserve the HTML visual style as faithfully as possible, since many users will save and share it.

The disclaimer "Esto no es asesoría legal" is not decoration, it is structural: it appears in the header, footer, before each list of critical findings, and in the body of the delivery email. The Art. 1686 CC warning (absence of rescission for gross disparity in El Salvador) appears per configured policy.

---

## 2. Scope

**In scope:**

- Composition of the complete HTML report from `ContractAnalysis`, `Project`, and `LegalChunk` (via F3 to regenerate citations)
- Generation of the eight sections defined in `RUBRICA_CONTRATO.md` §11.1
- Responsive rendering: the HTML must work well from 360 px wide screens to 1920 px
- HTML-to-PDF conversion using WeasyPrint, preserving the visual style
- Mandatory inclusion of the disclaimer in header, footer, and before critical findings
- Conditional inclusion of the Art. 1686 CC warning per policy
- Simple visualizations (horizontal bars for score and economic comparisons) in inline SVG
- Versioning: each report includes `rubric_version`, `corpus_version`, `benchmark_version`
- On-demand regeneration: the report is not persisted; built when the link is accessed
- Limited i18n support (Spanish only for now) with separate templates to ease v2
- Handling of anonymized analyses: if the analysis has been anonymized, the report shows only what survives (summary, band, severity counts) and declares the anonymization to the user

**Out of scope:**

- Persisting the generated HTML or PDF
- Allowing edit or annotation of the report
- Serving the report via public link (that is F7)
- Sending the report via SMS or email (that is F7)
- Internationalization to English or another language
- Alternative templates chosen by the user (single format)
- Export to formats other than HTML and PDF (no .docx, no .json for the user)
- Visual customization per real estate project or developer
- Side-by-side comparison of multiple reports
- Separate printable version (the PDF suffices)
- Animations or complex interactivity (only expand/collapse blocks)

---

## 3. User Stories

### US-01: System composes the complete HTML report

**As the** system,
**I want to** generate the HTML report when requested,
**So that** F7 serves it to the user via the chosen channel.

**Acceptance criteria:**

- F6 exposes a function `generate_report_html(analysis_id, options)` invokable internally
- The function reads `ContractAnalysis` by `analysis_id`
- If the analysis does not exist, returns explicit error
- If the analysis is anonymized (`anonymized_at IS NOT NULL`), it generates the reduced version (see US-08)
- If the analysis is in `pending` or `failed` state, returns error
- If all is in order, it composes the eight defined sections:
  1. Header with identification
  2. Overall verdict
  3. Economic analysis
  4. Breakdown by category
  5. Highlighted findings
  6. Referenced legal bases
  7. Suggested actions
  8. Footer
- Renders HTML using a template engine (Jinja2)
- The HTML is self-contained: inline CSS or in a `<style>` block, no external dependencies, no JavaScript (except optional expand/collapse)
- The HTML passes basic W3C validation
- The HTML renders correctly in Chrome, Firefox, Safari (mobile and desktop)

**HTML structure returned (the user-facing text remains in Spanish):**

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex, nofollow">
    <title>Análisis de Contrato Casa Segura — {short_id}</title>
    <style>
        /* Inline CSS embedded here */
    </style>
</head>
<body>
    <header class="cs-header">
        <!-- Logo, ID, date, contract type, project, disclaimer -->
    </header>

    <section class="cs-verdict">
        <!-- Large score, band, executive summary, override box if applicable -->
    </section>

    <section class="cs-economic" data-section="economic">
        <!-- Figures table, comparisons, overcost, Art. 1686 warning if applicable -->
    </section>

    <section class="cs-categories" data-section="categories">
        <!-- 6 collapsible blocks, one per category -->
    </section>

    <section class="cs-findings" data-section="findings">
        <!-- Prioritized findings with disclaimer at start if there are critical ones -->
    </section>

    <section class="cs-legal-refs" data-section="legal-refs">
        <!-- List of cited articles -->
    </section>

    <section class="cs-actions" data-section="actions">
        <!-- 3 blocks: ask the seller, take to lawyer, documents to demand -->
    </section>

    <footer class="cs-footer">
        <!-- Extended disclaimer, versions, hash, contact for errors -->
    </footer>

    <script>
        /* Only expand/collapse; no external calls */
    </script>
</body>
</html>
```

---

### US-02: System renders header with prominent disclaimer

**As the** system,
**I want to** display clear analysis identification and disclaimer in the header,
**So that** the user knows what document they are looking at and understands the product's limits.

**Acceptance criteria:**

- The header contains:
  - Logo and "Casa Segura" wordmark
  - Text "Análisis de Contrato Inmobiliario"
  - Short analysis ID (`public_short_id`, format `CS-YYYY-XXXXXX`)
  - Analysis date in readable Salvadoran format (10 de mayo de 2026)
  - Detected contract type, with a note if reclassified
  - Extracted real estate project name, with note "el nombre se extrajo del contrato; no se verificó contra fuente externa"
  - Prominent disclaimer: "Este reporte no es asesoría legal. Antes de firmar, consulta a un abogado."
- If a type reclassification occurred (e.g. CVP → LEA), the header declares it: "Presentado como compraventa, reclasificado como leasing financiero. Mira la sección de hallazgos para detalles."
- The header disclaimer has a light yellow background and border to stand out
- On mobile view (< 600px), the header reflows to a single column and stays legible

---

### US-03: System shows the overall verdict

**As the** system,
**I want to** show the score, band, executive summary, and override if applicable,
**So that** the user gets the main answer in the first 10 seconds of reading.

**Acceptance criteria:**

- The verdict section contains:
  - Score 0–10 shown large (60–80 px typography)
  - Score color per band:
    - Green: `#10B981` (tailwind emerald-500)
    - Yellow: `#F59E0B` (amber-500)
    - Red: `#EF4444` (red-500)
  - Band label with icon:
    - Green: 🟢 "Favorable"
    - Yellow: 🟡 "Negocia antes de firmar"
    - Red: 🔴 "Procede con cuidado"
  - Executive summary (the `executive_summary` F4 generated)
  - If an override is active:
    - Prominent red box titled "Hallazgo crítico"
    - List of active overrides with code and description
    - Message: "Este contrato contiene cláusulas que la ley salvadoreña declara nulas o establece como infracciones muy graves. Independientemente del resto del análisis, no firmes hasta resolver estos puntos."
- In high contrast, the score and band are legible even on low-quality monitors
- For color-blind users, icons and textual labels are used in addition to color

---

### US-04: System renders economic analysis

**As the** system,
**I want to** show the contract's economic figures with visual comparison against benchmarks,
**So that** the user concretely sees how much it costs versus the market.

**Acceptance criteria:**

- The economic-analysis section contains:
  - Table with key figures from `EconomicSummary`:
    - Cash price
    - Down payment (amount and percentage)
    - Financed amount
    - Term (in years)
    - Effective annual rate
    - Monthly payment
    - Total cost to pay
    - Total cost vs. cash multiplier
  - Each row shows the value and, where applicable, the visual indicator from `BenchmarkComparison`
  - SVG horizontal bars showing the contract value vs. benchmark, with clear labels
  - Highlighted overcost figure: "Pagas $X más que en un crédito de mercado"
  - List of "what changes would save you" from `EconomicSummary.overcost.what_changes_would_save`
- This section is included only if `economic_summary` is NOT null
- If the contract type has no relevant economic figures (pure cash CVC, ARC with minimal data), the section is omitted or reduced to a brief mention
- The Art. 1686 CC warning is shown at the end of this section if:
  - The type is CVC, CVP, APV, LEA, FSV (any purchase)
  - And the configured policy requires it (see BR-08)

**Comparison visualization (inline SVG):**

```
Tasa de interés
Contrato:    [████████████████████████] 18% anual
Benchmark:   [████████████]            9% anual
                              ↑
                    9 puntos sobre el mercado
```

---

### US-05: System shows breakdown by category

**As the** system,
**I want to** show the six categories with their partial score and list of criteria,
**So that** the user understands in which areas the contract complies and where it fails.

**Acceptance criteria:**

- One section per category with applicable criteria
- Category header: name, global weight, partial score with visual bar
- List of criteria within:
  - Each criterion: icon per score (green/yellow/red/gray), short title, score 0-10, justification
  - Unverifiable criteria: ⊘ gray icon, "Unverifiable" label, justification of why
  - Collapsed by default; the user can expand to view justification
- If a category has no criteria applicable to the contract type, it is omitted from the report (not shown as score 0)
- The visible total must match the weighted average computed by F4
- On mobile, criteria stack vertically; on desktop, in a 2-column grid

---

### US-06: System lists the highlighted findings

**As the** system,
**I want to** show severity-prioritized findings with legal citation when applicable,
**So that** the user knows exactly what is wrong and why.

**Acceptance criteria:**

- The findings section contains all findings ordered by severity (critical, red, yellow, green, unverifiable) and within each level by criterion weight
- If there are critical findings, the disclaimer "Esto no es asesoría legal" appears again at the start of the section because critical findings are the most sensitive
- Each finding renders:
  - Severity icon
  - Short title
  - Description
  - Evidence: cited contract clause in a box with monospaced typography ("quote" style); if no snippet, it is omitted
  - Legal basis: each `LegalReference` renders as:
    - "Ley de Protección al Consumidor, Art. 12: [corpus paraphrase]"
    - "Ver texto completo del artículo" button/link that expands `text_verbatim` if available
  - If no legal basis (`legal_basis: []`) and the finding has tag `market_based`, it is noted: "Hallazgo basado en práctica de mercado, no en violación legal específica"
  - If tag `unverifiable_legal`, it is noted: "No pudimos confirmar la base legal específica en nuestro corpus para este hallazgo"
  - Actionable recommendation in a bordered box
- If there are more than 25 findings, yellows and greens may collapse by default into an "Otros puntos de observación" section

**Visual example of a finding (rendered in Spanish to the user):**

```
🔴 CRÍTICO — Tasa de interés efectiva anual fuera de mercado

La tasa contratada es 18% anual, lo cual está 9 puntos porcentuales por encima
del benchmark del mercado salvadoreño para crédito hipotecario directo (9% anual).

Cláusula citada del contrato:
┌─────────────────────────────────────────────────┐
│ "Las cuotas mensuales devengarán intereses a la │
│ tasa del 1.5% mensual, calculados sobre el      │
│ saldo total adeudado."  (Cláusula 6.2)          │
└─────────────────────────────────────────────────┘

Bases legales:
• Ley de Protección al Consumidor, Art. 12
  En contratos de compraventa a plazos, los intereses se calculan sobre los
  saldos diarios pendientes de cancelar, con base en el año calendario.
  [Ver texto completo]

• Ley de Protección al Consumidor, Art. 19 lit. j
  El proveedor de servicios financieros debe informar la tasa anual efectiva.
  [Ver texto completo]

✏️ Recomendación:
Pídele al vendedor que (1) exprese la tasa como anual efectiva, (2) confirme
que el cálculo es sobre saldos diarios pendientes y no sobre el saldo total,
(3) considere reducir la tasa al rango de mercado (8-10% anual).
```

---

### US-07: System renders suggested actions

**As the** system,
**I want to** show the user what to do concretely with the report,
**So that** the report is action-conducive and not merely informational.

**Acceptance criteria:**

- The actions section contains three blocks:
  1. "Antes de firmar, pídele al vendedor": list derived from the recommendations of critical and red findings
  2. "Lleva esto a tu abogado": list of key points for the user to open an informed conversation with a lawyer, generated by LLM from the analysis
  3. "Documentos que debes exigir": actionable list of documents per category D criteria (property risks) and other relevant
- Each block has a max of 5 items to avoid overwhelming
- The "Lleva al abogado" block is generated with a specific prompt (§8.1)
- If the band is green, block 1 may be empty; instead show "El contrato luce favorable en general. Igual revisa con tu abogado antes de firmar."
- Block 3 is generated based on `elements_detected` and category D findings
- Each item in block 1 includes a reference to the origin finding (internal link)

---

### US-08: System handles anonymized analyses

**As the** system,
**I want to** generate a reduced version of the report when the analysis is anonymized,
**So that** a user who returns to the link after 90 days receives honest information.

**Acceptance criteria:**

- If `ContractAnalysis.anonymized_at IS NOT NULL`, the report:
  - Shows normal header
  - Shows score and band
  - Shows executive summary (preserved)
  - Shows severity counts (critical, red, yellow, green, unverifiable)
  - Shows economic summary in buckets ("rate between 15-20%" instead of the exact value)
  - Does NOT show cited contract clauses (not preserved)
  - Does NOT show detailed per-criterion justifications
  - Does NOT show specific actionable recommendations
  - Declares visibly: "Este análisis fue anonimizado el [fecha] para proteger tu privacidad. Solo conservamos el resumen agregado. Si necesitas el análisis completo, sube el contrato de nuevo."
- In practice links expire at 30 days, so this case only applies if the user has the short ID without having regenerated

---

### US-09: System converts HTML to PDF

**As the** system,
**I want to** convert the report HTML to a downloadable PDF,
**So that** F7 delivers it via email and the user can save it on their device.

**Acceptance criteria:**

- F6 exposes function `generate_report_pdf(analysis_id, options)` which internally calls `generate_report_html` and then converts
- WeasyPrint is used as the conversion engine
- The PDF preserves the HTML's visual style as faithfully as possible
- Page size: Letter (210x279mm) or A4 per configuration
- Margins: 1.5 cm per side
- The PDF includes:
  - Page numbering in the footer
  - Analysis identification on each page (page header, distinct from the HTML header)
  - The Casa Segura logo as a subtle background watermark
- The resulting PDF weighs under 1 MB for typical analyses
- Conversion time: under 5 seconds for typical analyses
- If conversion fails, F6 returns a specific error and F7 handles the fallback (delivering the HTML via link instead of PDF via email)

---

### US-10: System versions the report

**As the** system,
**I want to** ensure that a report regenerated months later produces the same content,
**So that** the user who returns to the link sees consistency.

**Acceptance criteria:**

- The report always uses `ContractAnalysis.rubric_version`, `corpus_version`, and `benchmark_version` as stored in the row
- If those versions no longer exist in the system (which should not happen because they are immutable), F6 returns an explicit error
- F6 templates are also versioned: every major change in the report format is a new template version
- `ContractAnalysis.report_template_version` is optional to record which template version was used (if not specified, the latest is used, assuming backward compatibility)
- The report footer declares: "Generado con rúbrica v1.0.0, corpus v2026-05-10, benchmarks v2026-Q2"
- Report hash: the system computes a deterministic hash of the HTML so the user can verify integrity: "Hash del análisis: ABC123..."

---

## 4. Business Rules

**BR-01:** Neither the HTML nor the PDF of the report is persisted to disk or database. They are generated on demand. This preserves the privacy promise and simplifies retention.

**BR-02:** The disclaimer "Esto no es asesoría legal" appears in the header, footer, and before critical findings. It is invariant; it cannot be disabled by configuration.

**BR-03:** The report always uses the rubric, corpus, and benchmark versions stored in `ContractAnalysis`, not the system's current ones. This guarantees reproducibility.

**BR-04:** The report is in Salvadoran Spanish, with "tú" address, no dynamic localization.

**BR-05:** The report NEVER reproduces the full text of the user's contract. Only specific clauses cited as evidence of findings, and only in the render session (not persisted).

**BR-06:** Logos of banks, trade associations, or institutions cited as benchmark sources (BCR, ABANSA, FSV, IVU) are NOT reproduced in the report. Only text.

**BR-07:** The report of an anonymized analysis is an honest degraded version, not an error. It shows what survives anonymization with explicit declaration.

**BR-08:** The policy for when to display the Art. 1686 CC warning is in configuration:
- `art_1686_warning_mode = "always"`: in every purchase report
- `art_1686_warning_mode = "when_red"`: only when band is red
- `art_1686_warning_mode = "never"`: never (not recommended)
- Default: `always`

**BR-09:** The report includes a note about the project name: "El nombre del proyecto se extrajo del contrato; no se verificó contra fuente externa."

**BR-10:** The report includes a final note about the Project entity if the project has been analyzed more than once: "Casa Segura ha analizado N contratos de este proyecto. Score promedio de los análisis: X.X." This line does NOT include identifiers of other users or details of other analyses.

**BR-11:** The report offers an error-reporting mechanism: a link or instruction to write to `errores@casasegura.sv` mentioning the `public_short_id`.

**BR-12:** The report declares the rubric and corpus versions used so a reviewer (lawyer, journalist) can verify the content against original sources.

**BR-13:** No external JavaScript. The only JS allowed is inline for expand/collapse blocks. This avoids security risks and lets the report work offline once downloaded.

**BR-14:** The report does not load external resources (web fonts, remote images, CDN scripts). Everything is embedded or omitted. This preserves privacy (no tracking) and ensures the report looks the same offline.

---

## 5. Data Models

F6 does not create entities of its own. It only reads from `ContractAnalysis`, `Project`, `LegalChunk`, `LegalDocument`, and `RubricVersion`.

For observability, an optional table is suggested:

```sql
CREATE TABLE IF NOT EXISTS report_generation_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL,
    public_short_id TEXT NOT NULL,
    format TEXT NOT NULL CHECK (format IN ('html', 'pdf')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    generation_time_ms INTEGER,
    status TEXT NOT NULL CHECK (status IN ('success', 'failed')),
    error_code TEXT,
    bytes_generated INTEGER,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days')
);

CREATE INDEX idx_report_gen_log_analysis ON report_generation_log(analysis_id);
CREATE INDEX idx_report_gen_log_expires ON report_generation_log(expires_at);
```

---

## 6. Integration Points

### 6.1 Consumes: F4 (full ContractAnalysis) and F3 (legal citations)

F6 reads `ContractAnalysis` directly from the database. For legal citations, `LegalReference` rows are already embedded in the findings (F4 placed them via F3). F6 only needs F3 if it wants to show the additional `text_verbatim` of the article ("See full text" button), loaded on demand in the frontend or at render time.

### 6.2 Consumed by: F7 (Multi-Channel Delivery)

F7 invokes F6:
- `f6.generate_report_html(analysis_id)` to serve via web link
- `f6.generate_report_pdf(analysis_id)` to attach in email

### 6.3 Technical dependencies

| Dependency | Version | Use |
|---|---|---|
| `jinja2` | ≥ 3.1 | Template engine |
| `weasyprint` | ≥ 60 | HTML→PDF conversion |
| `pydyf` | ≥ 0.10 | WeasyPrint dependency |
| `pillow` | ≥ 10 | Logo/icon processing for PDF |
| `cssutils` | ≥ 2.10 | CSS validation (optional) |

### 6.4 Templates

Jinja2 templates live in the repository:

```
templates/
├── report/
│   ├── v1/
│   │   ├── full.html.j2         # Full template
│   │   ├── anonymized.html.j2   # Template for anonymized analyses
│   │   ├── _header.html.j2
│   │   ├── _verdict.html.j2
│   │   ├── _economic.html.j2
│   │   ├── _categories.html.j2
│   │   ├── _findings.html.j2
│   │   ├── _legal_refs.html.j2
│   │   ├── _actions.html.j2
│   │   ├── _footer.html.j2
│   │   └── style.css
│   └── v2/  # when released
```

### 6.5 Configuration

- `REPORT_TEMPLATE_VERSION` env var (default `v1`)
- `REPORT_PDF_PAGE_SIZE` env var (default `Letter`)
- `REPORT_PDF_MARGIN_CM` env var (default `1.5`)
- `REPORT_INCLUDE_ART_1686_WARNING` env var (default `always`)
- `REPORT_MAX_FINDINGS_BEFORE_COLLAPSE` env var (default `25`)

---

## 7. API Surface

F6 does not expose public endpoints. Only internal APIs consumed by F7.

For QA the following is exposed:

### 7.1 `GET /v1/internal/reports/{analysis_id}/html?template_version=v1` (requires `X-Internal-Auth`)

Generates and returns the HTML for inspection.

### 7.2 `GET /v1/internal/reports/{analysis_id}/pdf?template_version=v1` (requires `X-Internal-Auth`)

Generates and returns the binary PDF.

### 7.3 `POST /v1/internal/reports/preview` (requires `X-Internal-Auth`)

Renders a report from a mock analysis to preview templates in development.

```json
{
    "mock_analysis": { },
    "template_version": "v1",
    "format": "html"
}
```

---

## 8. LLM Prompts

F6 uses an LLM only to generate the "Lleva esto a tu abogado" block of the suggested-actions section.

### 8.1 "Take to lawyer" prompt

**System (kept in Spanish to keep tone "tú" calibrated for Salvadoran user):**

```
Eres asesor que ayuda a una persona común a preparar una conversación con un abogado sobre un contrato inmobiliario salvadoreño. Tu tarea es generar 3-5 puntos clave que el usuario debe llevar a la conversación, con base en los hallazgos del análisis.

Reglas:
1. Lenguaje "tú", claro, sin jerga legal innecesaria.
2. Cada punto es una oración o dos máximo.
3. Cada punto debe ser una pregunta o un tema, no un consejo legal.
4. Si hay findings críticos, prioriza ellos.
5. No inventes detalles del contrato. Usa solo lo que se te da.

Devuelve un JSON con la lista:
{"items": ["...", "...", "..."]}
```

**User:**

```
Tipo de contrato: {{contract_type}}
Score: {{score_total}}
Banda: {{band}}

Findings críticos y rojos:
{{findings_critical_and_red}}

Genera 3 a 5 puntos clave para llevar al abogado.
```

**Example output (delivered to user in Spanish):**

```json
{
    "items": [
        "Preguntale si la cláusula 6.2 que calcula intereses sobre el saldo total (no sobre el capital pendiente) viola realmente el Art. 12 LPC.",
        "Confirma con él si en El Salvador realmente no aplica la rescisión por lesión enorme (Art. 1686 CC) y qué significa eso para tu posición si firmas.",
        "Pregúntale si la cláusula que exime al vendedor del saneamiento por evicción puede ser nula y bajo qué condiciones.",
        "Explora si conviene negociar la tasa al rango de mercado bancario (8-10%) en lugar del 18% que el contrato establece."
    ]
}
```

---

## 9. Non-Functional Requirements

- **HTML generation P50 latency:** under 500 ms.
- **HTML generation P95 latency:** under 1.5 seconds.
- **PDF generation P50 latency:** under 3 seconds.
- **PDF generation P95 latency:** under 6 seconds.
- **Typical HTML size:** under 200 KB.
- **Typical PDF size:** under 1 MB.
- **Browser compatibility:** Chrome 100+, Firefox 100+, Safari 15+, Edge 100+, no polyfills.
- **Mobile:** legible on a 360 px wide screen.
- **Offline rendering:** once downloaded, the HTML looks the same without connection.
- **Accessibility:** correct HTML semantics, WCAG AA color contrast, text alternatives for icons.
- **Idempotency:** the same `analysis_id` produces the same HTML byte-by-byte (except for timestamp if included).
- **Cost:** zero external calls in HTML generation; one optional LLM call for the "lleva al abogado" block (bounded).
- **Observability:** Prometheus metrics for generation latency, failure rate, average PDF size.

---

## 10. Open Questions

1. What happens when PDF fails but HTML worked? Proposed strategy: F7 delivers HTML via link and notifies the user that the PDF was unavailable. Product must confirm.

2. Does the report show the F2 classification `confidence` to the user? Pros: transparency. Cons: confusion, "92% confidence" can be misinterpreted.

3. Should the report template be customizable for white-labeling? For example, if Casa Segura licenses the engine to a bank, is different branding allowed? This opens complexity (multiple templates) and should be v2.

4. Does the "Lleva al abogado" block use an LLM or is it generated with deterministic rules? LLM is more natural but introduces variability. Rules are rigid. Proposal: LLM in MVP, evaluate.

5. Does the report show a "what comes next" section with contextualized next steps? For example, "after speaking with the lawyer, return to the seller with this list". Product must define if it enters MVP.

6. Should the PDF be digitally signed for authenticity? Casa Segura could sign the PDF with a key so the user presents it to the seller with authority. This introduces cryptographic complexity and could give the impression of legal advice (against the disclaimer).

7. Should the visualizations (comparison bars) be interactive in HTML? For example, hover shows details. My proposal is no, keep simple.

8. Is downloading the report as JSON allowed for third parties wanting to process it programmatically? It goes against the privacy posture if the JSON contains findings with cited clauses. Recommend no.

---

**End of document.**
