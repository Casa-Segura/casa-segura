# Casa Segura — Domain Model

**Version:** 1.0
**Purpose:** Exhaustive catalog of system entities, their attributes, relationships, lifecycle, and persistence type. Serves as cross-cutting reference for every per-feature PRD.

---

## 1. Entity classification by persistence

The system has four entity types based on persistence:

**Persistent:** exist in the relational database with indefinite life or governed by a retention policy. Support query, indexing, and aggregation.

**Transient:** exist in the database during analysis processing (typically less than 24 hours) and are discarded afterward. They exist for idempotency, retry, and pipeline observability.

**Embedded:** live inside a JSONB field of a persistent entity. They have no table of their own. They are versioned together with their container.

**Static (catalog):** defined in code or in versioned configuration files. They do not change through user interaction. They are loaded at startup and referenced by key.

---

## 2. Complete entity catalog

| Entity | Type | Lifetime | Purpose |
|---|---|---|---|
| `Project` | Persistent | Indefinite | Real estate project; unit of intelligence aggregation |
| `ContractAnalysis` | Persistent | 90 days full, indefinite anonymized | The analysis applied to a contract |
| `RubricVersion` | Persistent catalog | Indefinite | Semantic version of the rubric used |
| `CorpusVersion` | Persistent catalog | Indefinite | Version of the legal corpus used |
| `LegalDocument` | Persistent catalog | Indefinite | Legal document (one full law) of the corpus |
| `LegalChunk` | Persistent catalog | Indefinite | Indexable corpus fragment (an article or sub-article) |
| `Criterion` | Persistent catalog | Indefinite | A rubric criterion (static definition) |
| `EconomicBenchmark` | Persistent catalog | Indefinite | A configurable market benchmark |
| `ContractSubmission` | Transient | 24 hours | Contract upload in processing |
| `OcrJob` | Transient | 24 hours | Text extraction job |
| `DeliveryRequest` | Transient | 7 days | Report delivery request |
| `CategoryScore` | Embedded in `ContractAnalysis` | same as container | Score per category within the analysis |
| `CriterionEvaluation` | Embedded in `ContractAnalysis` | same as container | Individual evaluation of a criterion |
| `Finding` | Embedded in `ContractAnalysis` | same as container | Finding identified in the analysis |
| `LegalReference` | Embedded in `Finding` | same as container | Verbatim citation from the corpus |
| `EconomicSummary` | Embedded in `ContractAnalysis` | same as container | Economic summary of the analysis |
| `BenchmarkComparison` | Embedded in `EconomicSummary` | same as container | A comparison against a benchmark |
| `ContractType` | Static enum | N/A | Contract type |
| `Band` | Static enum | N/A | Score band (green/yellow/red) |
| `Severity` | Static enum | N/A | Finding severity |
| `DeliveryChannel` | Static enum | N/A | Report delivery channel |
| `ExtractionStrategy` | Static enum | N/A | Strategy used to extract text |

---

## 3. Persistent entities with business life

### 3.1 Project

Represents a real estate project identified by its canonical name as it appears in the contracts. It is the system's unit of aggregate intelligence.

**Attributes:**

- `id` (UUID, PK) — Internal identifier
- `canonical_name` (TEXT, NOT NULL) — Name as it typically appears in the contracts
- `normalized_name` (TEXT, NOT NULL, UNIQUE) — Normalized slug: lowercase, no accents, no special characters, no redundant spaces
- `first_seen` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW()) — When the project was created in the system
- `last_analyzed` (TIMESTAMPTZ, NOT NULL) — Last time an analysis was associated
- `total_analyses` (INTEGER, NOT NULL, DEFAULT 0) — Count of associated analyses
- `avg_score` (NUMERIC(3,1)) — Moving average of associated total scores
- `score_distribution` (JSONB) — Count by band: `{green: N, yellow: M, red: K}`
- `metadata` (JSONB, DEFAULT '{}') — Extensible for future uses: general location, project type, first contract type seen

**Constraints:**

- `normalized_name` is the matching key when a new contract arrives
- `avg_score` is recomputed with each new analysis or anonymization (not maintained inline via triggers; computed on aggregate)
- `metadata` never contains PII

**Lifecycle:**

- Created on the first analysis whose `project_name_normalized` does not match any existing project
- Updated on each associated analysis (increments `total_analyses`, updates `last_analyzed`, recomputes `avg_score`)
- Never deleted, even though its individual analyses are anonymized after 90 days

**Relationships:**

- `Project 1 — N ContractAnalysis` (one project has many analyses)

---

### 3.2 ContractAnalysis

Represents the result of the analysis applied to a specific contract. It is the system's central entity from the user's perspective.

**Attributes:**

- `id` (UUID, PK) — Internal identifier
- `public_short_id` (TEXT, NOT NULL, UNIQUE) — Short identifier visible to the user, format `CS-YYYY-XXXXXX`
- `project_id` (UUID, NOT NULL, FK Project) — Associated project
- `contract_type` (TEXT, NOT NULL, CHECK enum) — Final detected type
- `contract_type_declared` (TEXT, CHECK enum, NULLABLE) — Type the document claims to be (may differ if reclassified)
- `contract_type_reclassified` (BOOLEAN, NOT NULL, DEFAULT FALSE) — Whether reclassification occurred
- `reclassification_reason` (TEXT, NULLABLE) — Justification for reclassification, citing indicators
- `score_total` (NUMERIC(3,1), NOT NULL, CHECK 0 ≤ x ≤ 10) — Final score
- `band` (TEXT, NOT NULL, CHECK enum) — Band
- `override_triggered` (TEXT[], NULLABLE) — List of active override codes
- `scores_by_category` (JSONB, NOT NULL) — Array of `CategoryScore`
- `criterion_evaluations` (JSONB, NOT NULL) — Array of `CriterionEvaluation`
- `findings` (JSONB, NOT NULL) — Array of `Finding`
- `findings_count` (INTEGER, NOT NULL) — Total count of findings (denormalized for query)
- `critical_findings_count` (INTEGER, NOT NULL) — Count of `critical` severity findings
- `unverifiable_count` (INTEGER, NOT NULL) — Count of unverifiable criteria
- `economic_summary` (JSONB, NULLABLE) — `EconomicSummary` when applicable to the contract type
- `rubric_version` (TEXT, NOT NULL) — Rubric version used
- `corpus_version` (TEXT, NOT NULL) — Corpus version used
- `benchmark_version` (TEXT, NOT NULL) — Version of the benchmarks file used
- `delivery_status` (TEXT, NOT NULL, CHECK enum, DEFAULT 'pending') — Report delivery state
- `delivery_channel` (TEXT, CHECK enum, NULLABLE) — Channel chosen by the user
- `delivery_target_hash` (TEXT, NULLABLE) — Salt+SHA-256 hash of email or phone
- `link_expires_at` (TIMESTAMPTZ, NULLABLE) — Web link expiration
- `anonymized_at` (TIMESTAMPTZ, NULLABLE) — If anonymized, when
- `submission_hash` (TEXT, NOT NULL) — SHA-256 of the original contract, for idempotency
- `created_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())

**Constraints:**

- `submission_hash` allows detection of re-submissions of the same contract
- `public_short_id` is generated with a year prefix for legibility
- `delivery_target_hash` is erased when the anonymization job runs
- After `anonymized_at`, the fields `criterion_evaluations`, `findings`, and the exact values of `economic_summary` are reduced to discrete buckets
- `submission_hash` is preserved after anonymization for future deduplication

**Lifecycle:**

- State `pending` at creation
- Transitions to `sent_email`, `sent_whatsapp`, or `available_link` after successful delivery
- Transitions to `expired` when `link_expires_at < NOW()`
- At 90 days the anonymization job runs and:
  - Erases `delivery_target_hash`
  - Reduces exact values of `economic_summary` to buckets
  - Reduces `criterion_evaluations` to only the per-category aggregate
  - Reduces `findings` to only the count per severity
  - Sets `anonymized_at` with timestamp
- After anonymization the analysis is not deleted; its metrics still contribute to the Project

**Relationships:**

- `ContractAnalysis N — 1 Project`
- `ContractAnalysis 1 — N DeliveryRequest` (each analysis may have multiple delivery attempts)
- `ContractAnalysis N — 1 RubricVersion` (referenced by `rubric_version`)
- `ContractAnalysis N — 1 CorpusVersion` (referenced by `corpus_version`)

**Recommended indexes:**

- `idx_contract_analysis_project_id` for listing analyses of a project
- `idx_contract_analysis_public_short_id` for lookup by short ID
- `idx_contract_analysis_submission_hash` for deduplication
- `idx_contract_analysis_link_expires_at` for the expiration job
- `idx_contract_analysis_anonymized_at_null` partial for the anonymization job

---

### 3.3 RubricVersion

Semantic version of the evaluation rubric. Immutable catalog.

**Attributes:**

- `version` (TEXT, PK) — Semver, e.g. `1.0.0`
- `released_at` (TIMESTAMPTZ, NOT NULL) — When this version was released
- `criteria_count` (INTEGER, NOT NULL) — Total criteria in this version
- `categories` (JSONB, NOT NULL) — Definition of categories and their global weights
- `criteria_definitions_path` (TEXT, NOT NULL) — Path to the YAML file with the criteria for this version
- `changelog` (TEXT) — Summary of changes versus the previous version

**Constraints:**

- Immutable once published
- A new version is a new row, not an UPDATE

**Lifecycle:**

- INSERT only
- No DELETE

---

### 3.4 CorpusVersion

Version of the legal corpus used in a specific retrieval. Allows reproducing analyses with the legal citations from the correct version.

**Attributes:**

- `version` (TEXT, PK) — Versioned by date or by corpus commit hash, e.g. `2026-05-10`
- `released_at` (TIMESTAMPTZ, NOT NULL)
- `laws_count` (INTEGER, NOT NULL) — Total laws in this version
- `articles_count` (INTEGER, NOT NULL) — Total indexed articles
- `chunks_count` (INTEGER, NOT NULL) — Total vectorized chunks
- `manifest` (JSONB, NOT NULL) — List of included laws with their identifiers
- `changelog` (TEXT)

**Constraints:**

- Immutable once published
- `LegalChunk` rows are associated with a specific corpus version

---

### 3.5 LegalDocument

Full legal document of the corpus (one whole law).

**Attributes:**

- `law_id` (TEXT, PK) — Slug, e.g. `ley-inquilinato`
- `corpus_version` (TEXT, NOT NULL, FK CorpusVersion) — Version it belongs to
- `title` (TEXT, NOT NULL) — Official title
- `short_title` (TEXT) — Short title for citations
- `decree` (TEXT) — Decree number and date
- `issued_at` (DATE) — Original issuance date
- `official_gazette` (TEXT) — Reference to the official gazette (Diario Oficial)
- `last_verified` (DATE) — Last date verified against the official source
- `source_url` (TEXT) — URL of the official source
- `status` (TEXT, CHECK ['in_force', 'repealed', 'in_force_with_amendments']) — Current status
- `subject` (TEXT) — Area of law

**Constraints:**

- `(law_id, corpus_version)` is UNIQUE: the same `law_id` may exist in multiple corpus versions with changes

---

### 3.6 LegalChunk

Indexable corpus fragment, typically an article or a sub-article. It is the RAG retrieval unit.

**Attributes:**

- `id` (UUID, PK)
- `law_id` (TEXT, NOT NULL, FK LegalDocument)
- `corpus_version` (TEXT, NOT NULL, FK CorpusVersion)
- `article_number` (TEXT, NOT NULL) — E.g. `Art. 4`, `Art. 18`
- `anchor` (TEXT, NOT NULL) — Anchor slug, e.g. `art-4`
- `text_paraphrased` (TEXT, NOT NULL) — Curated paraphrase shown to the user
- `text_verbatim` (TEXT, NULLABLE) — Verbatim article text (may be long)
- `embedding` (VECTOR(384), NOT NULL) — Embedding of the paraphrased text for semantic search
- `tags` (TEXT[]) — Filter tags, e.g. `['warranty','eviction']`
- `relevance_for_findings` (TEXT[]) — Finding categories where it applies
- `severity_hint` (TEXT) — Suggested severity if the contract fails this article

**Constraints:**

- Embedding uses the `paraphrase-multilingual-MiniLM-L12-v2` model (384 dimensions)
- Semantic search uses `cosine_distance` with a configurable threshold (default 0.65)

**Recommended indexes:**

- `idx_legal_chunk_corpus_version` to filter by version
- `idx_legal_chunk_law_id` to list articles of a law
- `legal_chunk_embedding_idx` HNSW over embedding
- `idx_legal_chunk_tags` GIN over tags

---

### 3.7 Criterion

Definition of an individual rubric criterion.

**Attributes:**

- `id` (TEXT, PK) — Unique criterion identifier, e.g. `A1`, `B2`, `E7`
- `rubric_version` (TEXT, NOT NULL, FK RubricVersion)
- `category` (TEXT, NOT NULL, CHECK ['A','B','C','D','E','F'])
- `title` (TEXT, NOT NULL) — Short title of the criterion
- `description` (TEXT, NOT NULL) — What is being assessed
- `weight_in_category` (NUMERIC(4,2), NOT NULL) — Percentage weight within the category
- `applicable_types` (TEXT[], NOT NULL) — Contract types to which it applies
- `legal_anchor` (TEXT[], NOT NULL) — Law articles it is based on, e.g. `['art-1605-cc', 'art-4-ley-inquilinato']`
- `override_code` (TEXT, NULLABLE) — If it triggers an override, which code
- `evaluation_prompt` (TEXT, NOT NULL) — Prompt template for the LLM
- `scoring_scale` (JSONB, NOT NULL) — Definition of the 0-10 scale with textual criteria
- `worst_case_when_unverifiable` (NUMERIC, NOT NULL) — Score contributed if unverifiable

**Constraints:**

- Immutable within a rubric version
- Changes require a new rubric version

---

### 3.8 EconomicBenchmark

Market benchmark used in economic calculations. Configurable, versioned.

**Attributes:**

- `benchmark_key` (TEXT, PK) — Unique key, e.g. `bank_mortgage_rate_max`
- `benchmark_version` (TEXT, NOT NULL) — Benchmark version
- `value_min` (NUMERIC, NULLABLE)
- `value_max` (NUMERIC, NULLABLE)
- `value_default` (NUMERIC, NULLABLE)
- `unit` (TEXT, NOT NULL) — `pct`, `usd`, `months`, `multiplier`
- `applicable_contract_types` (TEXT[], NOT NULL)
- `source` (TEXT, NOT NULL) — Source citation
- `source_url` (TEXT)
- `last_updated` (DATE, NOT NULL)
- `next_review_due` (DATE, NOT NULL)

---

## 4. Transient entities

### 4.1 ContractSubmission

Contract upload in processing. Discarded after successful analysis or after 24 hours.

**Attributes:**

- `id` (UUID, PK)
- `submission_hash` (TEXT, NOT NULL, UNIQUE) — SHA-256 of the original file
- `file_format` (TEXT, NOT NULL, CHECK ['pdf','jpg','jpeg','png','heic','webp'])
- `file_size_bytes` (INTEGER, NOT NULL)
- `page_count` (INTEGER, NULLABLE)
- `received_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())
- `processing_status` (TEXT, NOT NULL, CHECK enum)
- `extraction_strategy_attempted` (TEXT, CHECK enum, NULLABLE)
- `extraction_strategy_successful` (TEXT, CHECK enum, NULLABLE)
- `extracted_text_token_count` (INTEGER, NULLABLE)
- `extracted_text_language` (TEXT, NULLABLE)
- `error_reason` (TEXT, NULLABLE)
- `error_code` (TEXT, NULLABLE)
- `analysis_id` (UUID, NULLABLE, FK ContractAnalysis) — Associated upon completion
- `expires_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW() + INTERVAL '24 hours')

**Constraints:**

- Cleanup job deletes rows with `expires_at < NOW()`
- Extracted text is NOT persisted; only `extracted_text_token_count` for audit
- Original file is NOT persisted to disk; only in memory during processing

**States (`processing_status`):**

- `received` — File received, awaiting processing
- `extracting` — Text extraction in progress
- `extracted` — Text extracted correctly
- `classifying` — Classification in progress
- `analyzing` — Rubric application in progress
- `completed` — Analysis complete, associated with `analysis_id`
- `failed_extraction` — Extraction failed
- `failed_classification` — Could not classify
- `failed_analysis` — Analysis failed
- `rejected_language` — Language not Spanish
- `rejected_type` — Contract type not covered
- `rejected_size` — Exceeds size or page limit

---

### 4.2 OcrJob

Individual text extraction job. Provides observability and retry.

**Attributes:**

- `id` (UUID, PK)
- `submission_id` (UUID, NOT NULL, FK ContractSubmission)
- `strategy` (TEXT, NOT NULL, CHECK ['pypdf', 'vision_llm', 'tesseract'])
- `started_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())
- `completed_at` (TIMESTAMPTZ, NULLABLE)
- `status` (TEXT, NOT NULL, CHECK ['running','success','failed','timeout'])
- `error` (TEXT, NULLABLE)
- `error_code` (TEXT, NULLABLE)
- `tokens_consumed` (INTEGER, NULLABLE) — For vision LLM
- `cost_estimate_cents` (INTEGER, NULLABLE) — Estimated call cost
- `attempt_number` (INTEGER, NOT NULL, DEFAULT 1)
- `expires_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW() + INTERVAL '24 hours')

**Constraints:**

- For a given `submission_id` there may be multiple `OcrJob` rows (one per attempt of each strategy)
- Cleanup job deletes rows with `expires_at < NOW()`

---

### 4.3 DeliveryRequest

Request to deliver the report to the user.

**Attributes:**

- `id` (UUID, PK)
- `analysis_id` (UUID, NOT NULL, FK ContractAnalysis)
- `channel` (TEXT, NOT NULL, CHECK enum)
- `target_hash` (TEXT, NOT NULL) — Hash of email or phone
- `target_value_encrypted` (TEXT, NOT NULL) — Original value encrypted with a KMS key; erased after successful delivery or 24 hours
- `requested_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW())
- `delivered_at` (TIMESTAMPTZ, NULLABLE)
- `attempt_count` (INTEGER, NOT NULL, DEFAULT 0)
- `max_attempts` (INTEGER, NOT NULL, DEFAULT 3)
- `status` (TEXT, NOT NULL, CHECK ['queued','sending','delivered','failed','expired'])
- `last_error` (TEXT, NULLABLE)
- `expires_at` (TIMESTAMPTZ, NOT NULL, DEFAULT NOW() + INTERVAL '7 days')

**Constraints:**

- `target_value_encrypted` is erased upon `status=delivered` or upon reaching `expires_at`
- `target_hash` is preserved for user retries with the short ID
- Retry policy: exponential backoff 30s, 5min, 30min

---

## 5. Entities embedded in JSONB

These entities have no table of their own; they live within the JSONB field of their container.

### 5.1 CategoryScore (inside `ContractAnalysis.scores_by_category`)

```json
{
  "category": "B",
  "category_name": "Economic health",
  "weight_global": 0.30,
  "weight_effective": 0.30,
  "score": 4.2,
  "criteria_count_total": 9,
  "criteria_count_applicable": 7,
  "criteria_count_unverifiable": 1
}
```

### 5.2 CriterionEvaluation (inside `ContractAnalysis.criterion_evaluations`)

```json
{
  "criterion_id": "B2",
  "category": "B",
  "applicable": true,
  "evaluated": true,
  "unverifiable": false,
  "score": 2.0,
  "override_triggered": null,
  "justification": "The contracted rate is 18% annual, 9 points above the market benchmark (9%). This falls in the 'severe' range per the B2 scale of the rubric.",
  "evidence_snippet": "Las cuotas mensuales devengarán intereses a la tasa del 1.5% mensual...",
  "weight_in_category": 0.20
}
```

### 5.3 Finding (inside `ContractAnalysis.findings`)

```json
{
  "id": "F-001",
  "severity": "critical",
  "title": "Effective annual interest rate out of market",
  "description": "The contracted interest rate is 18% annual, which is 9 percentage points above the market benchmark.",
  "evidence_clause_snippet": "Cláusula 6.2: Las cuotas mensuales devengarán intereses a la tasa del 1.5% mensual...",
  "legal_basis": [{"...": "LegalReference"}],
  "recommendation": "Ask the seller to (1) express the rate as effective annual, (2) confirm computation is on outstanding daily balances and not on the total balance, (3) consider reducing the rate to the market range (8-10% annual).",
  "related_criterion_id": "B2",
  "anchors_to_override": "art_12_lpc"
}
```

### 5.4 LegalReference (inside `Finding.legal_basis`)

```json
{
  "law_id": "ley-proteccion-consumidor",
  "law_title": "Ley de Protección al Consumidor",
  "article": "Art. 12",
  "anchor": "art-12",
  "paraphrased_quote": "In installment-purchase contracts, interest is computed on outstanding daily balances, based on the calendar year.",
  "official_source": "D.L. 776 de 2005",
  "corpus_version": "2026-05-10"
}
```

### 5.5 EconomicSummary (inside `ContractAnalysis.economic_summary`)

```json
{
  "contract_type": "CVP",
  "currency": "USD",
  "price_cash": 80000,
  "down_payment": 8000,
  "down_payment_pct": 0.10,
  "financed_amount": 72000,
  "term_months": 240,
  "annual_rate_pct": 0.18,
  "monthly_payment": 1083.50,
  "total_cost_paid": 268040,
  "total_cost_vs_cash_multiplier": 3.35,
  "overcost_vs_benchmark_usd": 95000,
  "benchmark_comparisons": [{"...": "BenchmarkComparison"}]
}
```

After 90-day anonymization, numeric fields are reduced to buckets:

```json
{
  "contract_type": "CVP",
  "currency": "USD",
  "price_cash_bucket": "60k-100k",
  "down_payment_pct_bucket": "10-15",
  "annual_rate_pct_bucket": "15-20",
  "term_months_bucket": "180-240",
  "anonymized": true
}
```

### 5.6 BenchmarkComparison (inside `EconomicSummary.benchmark_comparisons`)

```json
{
  "metric": "annual_rate",
  "metric_label": "Effective annual rate",
  "contract_value": 0.18,
  "benchmark_value": 0.09,
  "benchmark_key": "bank_mortgage_rate_mid",
  "delta_pct_points": 9.0,
  "assessment": "well_above_market"
}
```

`assessment` values: `within_market` | `above_market` | `well_above_market` | `below_market_favorable`

---

## 6. Enumerated types (static)

### 6.1 ContractType

```
CVC                 // Cash purchase
CVP                 // Installment purchase
ARV                 // Residential lease
ARC                 // Small commercial lease
APV                 // Lease with promise to sell
LEA                 // Real estate financial leasing
IVU                 // IVU institutional contract
FSV                 // FSV-financed purchase or loan
NOT_CLASSIFIABLE
```

### 6.2 Band

```
GREEN              // 8.0 - 10.0
YELLOW             // 5.0 - 7.9
RED                // 0 - 4.9
NOT_ANALYZABLE
```

### 6.3 Severity

```
CRITICAL           // active override or absolute nullity
RED                // serious deviation against the buyer
YELLOW             // negotiable observation
GREEN              // favorable or compliant
UNVERIFIABLE       // not extractable from the contract
```

### 6.4 DeliveryChannel

```
EMAIL_PDF
WHATSAPP_SUMMARY
WEB_LINK
```

### 6.5 ExtractionStrategy

```
PYPDF              // PDF with directly extractable text
VISION_LLM         // OpenRouter vision model (preferred for scans and images)
TESSERACT          // Local fallback with Tesseract
```

### 6.6 OverrideCode (the 11 critical overrides)

```
art_1605_cc                  // Sale of real property without public deed
art_1613_cc                  // Price at the discretion of one party
art_1644_cc                  // Bad-faith waiver of warranty
art_1425_cc                  // Promise without a definite term
art_3_ivu_family_homestead   // Attempt to transfer under Bien de Familia
art_5_lpc_non_waivable       // Waiver of non-waivable rights
art_12_lpc                   // Late interest on total balance
art_13_lpc                   // Unilateral modification
art_18_lpc_blank_signature   // Blank signature
art_17h_lpc_arbitration      // Arbitration imposed in adhesion contract
art_58_fsv                   // FSV annotation not disclosed
```

---

## 7. Relationships diagram (conceptual ER)

```
                     ┌─────────────────────────┐
                     │   RubricVersion         │
                     │   (catalog)             │
                     └──────────┬──────────────┘
                                │ 1
                                │
                                │ N
                     ┌──────────┴──────────────┐
                     │   Criterion             │
                     │   (catalog, 38 items)   │
                     └─────────────────────────┘

                     ┌─────────────────────────┐
                     │   CorpusVersion         │
                     │   (catalog)             │
                     └──────────┬──────────────┘
                                │ 1
                                │
                                │ N
                     ┌──────────┴──────────────┐
                     │   LegalDocument         │ 1───N    LegalChunk
                     │   (catalog)             │          (catalog)
                     └─────────────────────────┘

  ┌──────────────────┐    1
  │   Project        │────────────────┐
  │   (persistent)   │                │
  └──────────────────┘                │ N
                                      │
                            ┌─────────┴───────────────┐
                            │   ContractAnalysis      │ ─────► RubricVersion (rubric_version)
                            │   (persistent, 90d/∞)   │ ─────► CorpusVersion (corpus_version)
                            └─────────┬───────────────┘
                                      │ 1
                                      │
                                      │ N
                            ┌─────────┴───────────────┐
                            │   DeliveryRequest       │
                            │   (transient, 7d)       │
                            └─────────────────────────┘

  ┌──────────────────────┐
  │ ContractSubmission   │ ─── (on completion) ───► ContractAnalysis
  │ (transient, 24h)     │
  └──────────┬───────────┘
             │ 1
             │
             │ N
  ┌──────────┴───────────┐
  │   OcrJob             │
  │   (transient, 24h)   │
  └──────────────────────┘

Embedded in ContractAnalysis JSONB:
  - scores_by_category: CategoryScore[]
  - criterion_evaluations: CriterionEvaluation[]
  - findings: Finding[] (each with legal_basis: LegalReference[])
  - economic_summary: EconomicSummary (with benchmark_comparisons: BenchmarkComparison[])
```

---

## 8. Retention policy summary

| Entity | Full retention | Anonymized retention | Minimal retention |
|---|---|---|---|
| `Project` | Indefinite | N/A | N/A |
| `ContractAnalysis` | 90 days | Indefinite (bucketed) | N/A |
| `ContractSubmission` | 24 hours | N/A | N/A |
| `OcrJob` | 24 hours | N/A | N/A |
| `DeliveryRequest.target_value_encrypted` | Until successful delivery or 24h | N/A | N/A |
| `DeliveryRequest` (rest) | 7 days | N/A | N/A |
| `RubricVersion`, `CorpusVersion`, `LegalDocument`, `LegalChunk`, `Criterion`, `EconomicBenchmark` | Indefinite | N/A | N/A |

---

## 9. What is NOT persisted, explicitly

- Original contract file (PDF, image)
- OCR-extracted text of the contract
- Individual contract clauses (beyond the snippet shown in the report, which is discarded after rendering)
- Names of the parties (seller, buyer, landlord, tenant)
- Specific property address
- DUI, NIT, passport number, any personal identifier of the parties
- User email in clear (only hash and temporary encryption in `DeliveryRequest`)
- User phone in clear (idem)
- Generated HTML or PDF report (regenerated on demand; not saved)

---

**End of document.**
