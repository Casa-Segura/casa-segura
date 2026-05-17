# EconomicSummary JSON contract (FE / BE parity)

Cross-team normative contract for **`ContractAnalysis.economic_summary`** (JSONB). Used by **[CS-135](../../Roadmap/tickets/CS-135.md)**, **[CS-136](../../Roadmap/tickets/CS-136.md)**, **[EPIC-07](../../Roadmap/EPIC-07-report-generation.md)** (report section), and **`/r/{publicShortId}`** HTML when wired.

---

## Canonical shape

**Authority order (when sources disagree during CS-135):**

1. **[PRD_F5 US-07](../../Casa%20Segura%20Formal%20PRDs/PRD_F5_ANALISIS_ECONOMICO.md)** (“Expected structured output”) — nested `fields_extracted` / `fields_derived`, `overcost`, `warnings`, **`benchmark_version` inside JSON**.
2. **[CS-135](../../Roadmap/tickets/CS-135.md)** — extras `derivation_status`, `currency_conversion_note`; pydantic “forbid unknown keys”; dedupe **`warnings`** by `code` + `related_field`.
3. **[DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md)** §5.5–5.6 — conceptual / anonymization buckets; §5.5’s **flat** illustrative JSON is **not** the persisted v1 envelope (superseded by PRD nesting until DOMAIN_MODEL §5.5 is rewritten to match).

Example fixtures: [`docs/fixtures/economic-summary/`](../../fixtures/economic-summary/README.md).

---

## Top-level keys (snake_case)

| Key                     | Type                 | Required when                     | Notes                                                                                          |
| ----------------------- | -------------------- | --------------------------------- | ---------------------------------------------------------------------------------------------- |
| `contract_type`         | string               | Always                            | Values: `DOMAIN_MODEL` §6.1 enum (e.g. `CVP`, `FSV`, …).                                       |
| `currency`              | string               | Always                            | ISO-style code (`USD`; colones conventions per PRD F5 BR-04 later).                            |
| `currency_conversion_note` | string \| null    | Include once CS-135 ships           | Explain fixed-rate conversion when non-USD surfaced.                                         |
| `derivation_status`     | string \| null       | Omit or `"full"` in happy path     | **`insufficient_data`** per [PRD F5 BR-09](../../Casa%20Segura%20Formal%20PRDs/PRD_F5_ANALISIS_ECONOMICO.md); see **Partial payloads**. |
| `fields_extracted`      | object               | Always                            | Numeric raw fields; may be `{}` when unverifiable.                                               |
| `fields_derived`        | object               | Always                            | Derived metrics; may be `{}` when skipped.                                                     |
| `benchmark_comparisons` | array                | Always                            | **Never omit** — use `[]`; each item is `BenchmarkComparison` (below).                        |
| `overcost`              | object \| null       | Prefer key once schema frozen       | **`null`** when not applicable (e.g. segment rules BR-10/BR-11); object when computed.          |
| `warnings`              | array                | Always                            | **Never omit** — use `[]`; items are `Warning` (below); dedupe by `code` + `related_field`.     |
| `benchmark_version`     | string               | When economics ran                | Echo of catalog tag (**[CS-136](../../Roadmap/tickets/CS-136.md)** dual storage section).       |

**Forbidden:** unknown sibling keys (`extra_*`). When Django/Pydantic is configured **`extra='forbid'`** (**[CS-135](../../Roadmap/tickets/CS-135.md)** AC), payloads that include unrecognized keys fail validation on ingest or round-trip merges. Clients must **`PATCH`/assemble** blobs using **only** documented keys until ADR versioning explicitly adds fields.

Versioning (**[CS-010](../../Roadmap/tickets/CS-010.md)**, **[ADR-0004](../../adr/ADR-0004-versioning.md)**) covers **dropping optional fields** safely as the API evolves — it **does not** invite random extra keys from either direction; unpublished JSON keys remain an integration bug until documented.

## `null` vs omit (CS-135 alignment)

| Pattern                       | Convention                                                                                                      |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `benchmark_comparisons`, `warnings` | **Never omit keys** — use `[]`.                                                                                 |
| `fields_extracted`, `fields_derived` | **Never omit keys** — use `{}`.                                                                               |
| `overcost`                    | Prefer **`null`** when absent; assembler README documents any legacy omit.                                      |
| `currency_conversion_note`    | **`null`** when N/A once key exists.                                                                             |
| Inner numerics               | Omit vs `null` — **pick one rule per submodule** in pydantic; FE treats either as unset until tightened.        |

---

## `fields_extracted` / `fields_derived`

Mirrors **[CS-113](../../Roadmap/tickets/CS-113.md)** / **[CS-114](../../Roadmap/tickets/CS-114.md)** and **[CS-131](../../Roadmap/tickets/CS-131.md)**–**[CS-134](../../Roadmap/tickets/CS-134.md)** outputs. Snake_case fractions (e.g. `annual_rate_pct: 0.18`).

---

## `BenchmarkComparison` objects

PRD US-07 row shape; **`benchmark_source`** is required in this contract (DOMAIN_MODEL §5.6 snippet omits it — catalog parity / BR-13).

| Field               | Type            | Notes                                                                                             |
| ------------------- | --------------- | ------------------------------------------------------------------------------------------------- |
| `metric`            | string          | Machine id (`annual_rate`, `monthly_payment_ratio`, …).                                           |
| `metric_label`      | string          | Report copy.                                                                                      |
| `contract_value`    | number          | Same unit semantics as metric.                                                                     |
| `benchmark_value`   | number          | Reference comparison.                                                                              |
| `benchmark_key`     | string          | **[CS-130](../../Roadmap/tickets/CS-130.md)** YAML key; glossary: [`BENCHMARK_KEY_GLOSSARY.md`](../../fixtures/economic-summary/BENCHMARK_KEY_GLOSSARY.md). |
| `benchmark_source`  | string          | Short citation (`source`-like).                                                                   |
| `delta_pct_points`  | number \| null | `null` when N/A.                                                                                  |
| `assessment`        | string          | `within_market` \| `above_market` \| `well_above_market` \| `below_market_favorable` (DOMAIN_MODEL §5.6 baseline). |

---

## `overcost` object

| Field                      | Type     |
| -------------------------- | -------- |
| `vs_benchmark_usd`         | number   |
| `explanation`              | string   |
| `what_changes_would_save` | string[] |

---

## `warnings` objects

Per [PRD F5 US-06](../../Casa%20Segura%20Formal%20PRDs/PRD_F5_ANALISIS_ECONOMICO.md):

| Field                | Type            |
| -------------------- | --------------- |
| `code`               | string          |
| `severity_suggested` | `yellow` \| `red` |
| `description`        | string          |
| `related_field`      | string \| null  |

---

## Partial / degraded payloads (BR-09, **[CS-137](../../Roadmap/tickets/CS-137.md)**)

- Set `derivation_status` → **`insufficient_data`**
- `fields_extracted` / `fields_derived` may be `{}` — **never invent price/payment**
- `benchmark_comparisons`: `[]`
- `warnings`: optional explanatory rows
- `overcost`: **`null`**

Fixture: [`summary-insufficient-data.json`](../../fixtures/economic-summary/summary-insufficient-data.json).

---

## `benchmark_version` — dual storage & read surfaces (**[CS-136](../../Roadmap/tickets/CS-136.md)**)

**Persisted:**

- `contract_analysis.benchmark_version` (FK → economics `BenchmarkVersion`)
- **`economic_summary.benchmark_version`** — same logical string (**byte-for-byte** with column)

**Read targets for serializers:**

| Surface                        | Recommendation                                                          |
| ------------------------------ | ----------------------------------------------------------------------- |
| Analysis / submission REST     | Root-level **`benchmark_version`** next to **`economic_summary`**.       |
| `economic_summary` JSON        | Nested echo for self-contained report renderers.                         |
| **GET `/r/{public_short_id}`** | Footer trio + hash ([**F6** patterns](../F6_generacion_reporte/DESIGN_PATTERNS.md)). |
| Regenerated PDF                | Footer + **`benchmark_version`** in hash inputs                          |

**FE:** `analysis.benchmark_version ?? economic_summary?.benchmark_version` — assert parity once CS-136 enforced.

---

## Fixtures & churn

Bump fixture **`benchmark_version`** with intentional PRs (**[ADR-0004](../../adr/ADR-0004-versioning.md)** quarterly tag).
