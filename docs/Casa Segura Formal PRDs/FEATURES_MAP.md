# Casa Segura — Features Map

**Version:** 1.0
**Purpose:** Catalog of system features, their dependencies, the recommended implementation order, and the mapping to domain-model entities.

---

## 1. Feature catalog

The system decomposes into eight programmable features. Each will have its own detailed PRD.

| Code | Feature | Purpose |
|---|---|---|
| **F1** | Ingestion & Text Extraction Pipeline | Receive the contract, validate it, extract plain text using the optimal strategy |
| **F2** | Contract Classification & Structured Extraction | Identify contract type, extract project name, identify economic fields, reclassify disguised leasing |
| **F3** | Legal Corpus & Citation Retrieval (RAG) | Maintain the corpus, index articles, retrieve verbatim citations for findings under "cite or stay silent" discipline |
| **F4** | Rubric Engine & Score Calculation | Apply the 38 criteria to the classified contract, generate findings, compute category scores, detect overrides, compute final score |
| **F5** | Economic Analysis & Benchmarks | Compute derived economic figures, compare against configurable benchmarks, generate `EconomicSummary` |
| **F6** | Report Generation | Compose the HTML report with all pieces, render to PDF, manage versioning |
| **F7** | Multi-Channel Delivery & Link Management | Send via SMS, email, or serve via web link with TTL; manage redeliveries |
| **F8** | Persistence, Project Entity & Retention | Complete database schema, Project-matching logic, anonymization and cleanup jobs |

---

## 2. Dependency graph

```
                       ┌─────────────────────────────┐
                       │   F8: Persistence & DB      │  (horizontal: everything depends)
                       └─────────────┬───────────────┘
                                     │
       ┌─────────────────────────────┼─────────────────────────────┐
       │                             │                             │
       ▼                             ▼                             ▼
┌──────────────┐              ┌──────────────┐              ┌──────────────┐
│  F1: Ingest  │              │ F3: Corpus   │              │              │
│  + OCR       │              │  + RAG       │              │              │
└──────┬───────┘              └──────┬───────┘              │              │
       │                             │                      │              │
       ▼                             │                      │              │
┌──────────────┐                     │                      │              │
│  F2: Classif.│                     │                      │              │
└──────┬───────┘                     │                      │              │
       │                             │                      │              │
       ├────────────►┌──────────────┐│                      │              │
       │             │  F5: Economic│                      │              │
       │             │  Analysis    │                      │              │
       │             └──────┬───────┘                      │              │
       │                    │                              │              │
       │                    │                              │              │
       └────────────────────┼──────────────►┌──────────────┐              │
                            │               │  F4: Rubric  │              │
                            └──────────────►│  Engine      │              │
                                            └──────┬───────┘              │
                                                   │                      │
                                                   ▼                      │
                                            ┌──────────────┐              │
                                            │  F6: Report  │              │
                                            └──────┬───────┘              │
                                                   │                      │
                                                   ▼                      │
                                            ┌──────────────┐              │
                                            │  F7: Delivery│              │
                                            └──────────────┘              │
```

**How to read the graph:**

- **F8** is horizontal: it defines the database schema that all others use. It must be ready before any other feature can persist.
- **F1** and **F3** are the only ones that do not depend on other functional features (only on F8). They can be developed in parallel.
- **F2** depends only on **F1** (it needs extracted text).
- **F5** depends only on **F2** (it needs extracted economic fields).
- **F4** depends on **F2**, **F3**, and **F5** (it needs classification, citation retrieval, and economic analysis).
- **F6** depends on **F4** and **F5** (it needs findings + economic analysis).
- **F7** depends on **F6** (it needs the report to deliver).

---

## 3. Recommended implementation order

### Phase 0 — Base infrastructure
**F8 skeleton:** create the database schema with all persistent tables but without retention logic yet. System bootstrap.

### Phase 1 — Input pipelines (in parallel)
- **F1:** functional ingestion + OCR over PDF, image, and capture.
- **F3:** corpus ingested into Postgres + pgvector with basic semantic search.

### Phase 2 — Contract intelligence
- **F2:** type classification + field extraction. Depends on F1.

### Phase 3 — Analysis (in parallel)
- **F5:** economic computations and benchmark comparison. Depends on F2.
- Continue refining F3 with additional corpus articles.

### Phase 4 — Evaluation engine
- **F4:** rubric engine with the 38 criteria. Depends on F2, F3, F5.

### Phase 5 — User output
- **F6:** HTML + PDF report generation. Depends on F4 and F5.
- **F7:** multi-channel delivery (SMS, email, then web link). Depends on F6.

### Phase 6 — Privacy closure
- **F8 complete:** 90-day anonymization jobs, cleanup of transients, link expiration.

---

## 4. Feature → domain entities mapping

Which entities each feature creates, reads, updates, or deletes. Useful for coordinating development.

### F1: Ingestion & Text Extraction

| Entity | C | R | U | D |
|---|---|---|---|---|
| `ContractSubmission` | ✓ | ✓ | ✓ | ✓ (on expiration) |
| `OcrJob` | ✓ | ✓ | ✓ | ✓ (on expiration) |
| `ContractAnalysis` |  |  |  |  |
| `Project` |  |  |  |  |

### F2: Contract Classification

| Entity | C | R | U | D |
|---|---|---|---|---|
| `ContractSubmission` |  | ✓ | ✓ |  |
| `ContractAnalysis` | ✓ |  |  |  |

Output enriches `ContractAnalysis` with: `contract_type`, `contract_type_declared`, `contract_type_reclassified`, `reclassification_reason`, and prepares pre-parsed economic fields for F5.

### F3: Legal Corpus & RAG

| Entity | C | R | U | D |
|---|---|---|---|---|
| `LegalDocument` | ✓ | ✓ | ✓ (via new version) |  |
| `LegalChunk` | ✓ | ✓ | ✓ (via new version) |  |
| `CorpusVersion` | ✓ | ✓ |  |  |

F3 exposes an internal retrieval API: given a finding text, it returns the top-K `LegalChunk` most relevant with a similarity score. It only returns results above the threshold; it applies "cite or stay silent" discipline.

### F4: Rubric Engine

| Entity | C | R | U | D |
|---|---|---|---|---|
| `Criterion` |  | ✓ |  |  |
| `RubricVersion` |  | ✓ |  |  |
| `ContractAnalysis` |  |  | ✓ |  |
| `LegalChunk` (via F3) |  | ✓ |  |  |

Output enriches `ContractAnalysis` with: `criterion_evaluations`, `findings` (including `legal_basis`), `scores_by_category`, `override_triggered`, `score_total`, `band`, `findings_count`, `critical_findings_count`, `unverifiable_count`.

### F5: Economic Analysis

| Entity | C | R | U | D |
|---|---|---|---|---|
| `EconomicBenchmark` |  | ✓ |  |  |
| `ContractAnalysis` |  |  | ✓ |  |

Output enriches `ContractAnalysis` with: `economic_summary` and `benchmark_version`.

### F6: Report Generation

| Entity | C | R | U | D |
|---|---|---|---|---|
| `ContractAnalysis` |  | ✓ |  |  |
| `LegalChunk` |  | ✓ |  |  |
| `Project` |  | ✓ |  |  |

F6 does not persist the report. It regenerates on demand.

### F7: Multi-Channel Delivery

| Entity | C | R | U | D |
|---|---|---|---|---|
| `DeliveryRequest` | ✓ | ✓ | ✓ | ✓ (`target_value_encrypted` on delivery) |
| `ContractAnalysis` |  | ✓ | ✓ (`delivery_status`, `delivery_channel`, `delivery_target_hash`, `link_expires_at`) |  |

### F8: Persistence & Retention

Defines the entire schema. Implements the cron jobs:

- Cleanup of `ContractSubmission` and `OcrJob` with `expires_at < NOW()`
- Erasure of `DeliveryRequest.target_value_encrypted` after delivery or expiration
- Anonymization of `ContractAnalysis` with `created_at < NOW() - 90 days`
- Link expiration: sets `delivery_status = 'expired'` when `link_expires_at < NOW()`
- Recomputation of `Project.avg_score` when there are new analyses or anonymizations

---

## 5. Feature → user stories mapping (from PRD general)

How each PRD general user story is fulfilled by features.

| PRD general user story | Features that implement it |
|---|---|
| US-01: Upload contract | F1, F8 |
| US-02: Classify contract and extract project | F2, F8 |
| US-03: Apply rubric and produce score | F2, F3, F4, F5, F8 |
| US-04: Generate report with verbatim citations | F3, F6 |
| US-05: Receive report via channel | F6, F7 |
| US-06: Aggregate intelligence by Project | F8 |
| US-07: Retention and anonymization | F8 |

---

## 6. What does NOT fit any current feature

For traceability, these are the explicit exclusions reflecting the PRD general scope:

- Flow 1 (sign verification by photo) — out of MVP
- Web reputation search — out of product
- Developer blacklist — out of product
- Material verification against public registries — out of MVP, marked in findings as pending user verification
- User accounts and persistent authentication — out of product
- Personalized legal advice — out of scope by design

---

## 7. Rough complexity estimate by feature

Qualitative estimate for prioritization, not a schedule commitment.

| Feature | Complexity | Justification |
|---|---|---|
| F1 | Medium | OCR is a known problem; the routing between strategies is the challenge |
| F2 | Medium-high | Classification with LLM is straightforward; leasing reclassification requires a careful prompt |
| F3 | High | Corpus curation + chunking + indexing + threshold tuning |
| F4 | High | 38 criteria, each with its own prompt and scale |
| F5 | Medium | Economic computations are deterministic; the challenge is field-extraction robustness |
| F6 | Low-medium | HTML + WeasyPrint are straightforward; the challenge is the report's visual design |
| F7 | Medium | SMS provider and SMTP integration; error handling and retries |
| F8 | Medium | Schema + cron jobs are straightforward; the challenge is transactionality and consistency |

---

**End of document.**
