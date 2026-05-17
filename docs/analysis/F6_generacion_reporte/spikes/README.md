# Report generation spikes

Design-time prototypes for **`EPIC-07`** report HTML (**[EPIC-07](../../../Roadmap/EPIC-07-report-generation.md)**).

## Files

### `economic-section-spike.html`

- **[CS-203](../../../Roadmap/tickets/CS-203.md)** economics section (“bench bar”): **`benchmark_comparisons`**, **`overcost`**, **`warnings`**, and headline KPIs rendered from inlined JSON (**same shape as [`summary-warnings-heavy.json`](../../../fixtures/economic-summary/summary-warnings-heavy.json)**). Open directly in the browser (`file:` is fine).

**Accessibility**

- Landmarks (**`<main>`**), table **`caption`** (screen reader only summary), **`scope="col"`** on headers, and visually hidden **`Severidad`** text for alerts (severity strip remains decorative).

**Rubric / wording trace**

- User-facing headings and KPI labels mirror the economic transparency intent of **`RUBRICA_CONTRATO`** [§11 monetary clarity](../../../Casa%20Segura%20Formal%20PRDs/RUBRICA_CONTRATO.md); benchmark wording is aligned where possible with comparative economics in **`RUBRICA_CONTRATO`** [§14](../../../Casa%20Segura%20Formal%20PRDs/RUBRICA_CONTRATO.md); final approved copy stays with product/legal.

**`benchmark_key` mapping (until CS-130 YAML merges)**

- Provisional table: [`docs/fixtures/economic-summary/BENCHMARK_KEY_GLOSSARY.md`](../../../fixtures/economic-summary/BENCHMARK_KEY_GLOSSARY.md) (reconcile rows when **`economic_benchmarks.yaml`** ships in **[CS-130](../../../Roadmap/tickets/CS-130.md)**).

**Normative payload**

- Cross-team envelope: **[`ECONOMIC_SUMMARY_CONTRACT`](../../../analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md)**.
