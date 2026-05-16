# PRD: F8 — Persistence, Project Entity & Retention

**Version:** 1.0
**Status:** Approved for development
**Author:** Product Team
**Date:** 2026-05-10
**Depends on:** None (horizontal foundation feature)
**Blocks:** F1, F2, F3, F4, F5, F6, F7 (all depend on the schema)

---

## 1. Problem Statement

The seven functional features of the system produce and consume data. That database is not an implementation detail; it is a structural piece of the product because two central promises live in it: the Project entity as the unit of aggregate intelligence that accumulates across analyses, and the retention policy that materializes the privacy contract ("we don't keep your contract, we don't keep your personal data, after 90 days we anonymize everything").

F8 is the horizontal feature responsible for four things. First, define the complete database schema: each table with its columns, constraints, indices, and relationships, so the other features consume it without surprises. Second, implement the Project matching logic: when F2 extracts a normalized name, F8 looks it up, associates it, or creates a new one, and keeps aggregate metrics updated. Third, run the retention jobs: cleanup of transient submissions every 15 minutes, erasure of delivery targets after delivery, link expiration, and the 90-day anonymization that closes the privacy contract. Fourth, ensure transactional integrity for operations that cross several tables (an analysis with its findings, its Project entity, its delivery requests).

The feature does not expose direct functionality to the user, but its correct implementation is what lets the other seven keep their promises. If F8 fails, everything fails. If F8 stops anonymizing on time, the product lies about its privacy contract.

---

## 2. Scope

**In scope:**

- Complete database schema with all persistent and transient tables defined in `DOMAIN_MODEL.md`
- Versioned Django migrations (`manage.py migrate`) to evolve the schema without downtime
- Logic for `Project` entity creation/matching/update
- Computation and update of `Project.avg_score` and `score_distribution`
- Cron job `cleanup_transient`: deletes `contract_submission` and `ocr_job` with `expires_at < NOW()` (every 15 minutes)
- Cron job `cleanup_delivery_targets`: erases `target_value_encrypted` from `delivery_request` after successful delivery (every 5 minutes)
- Cron job `expire_links`: marks `contract_analysis` rows with `link_expires_at < NOW()` as `expired` (every hour)
- Cron job `anonymize_old_analyses`: anonymizes `contract_analysis` rows with `created_at < NOW() - 90 days` (daily)
- Cron job `recompute_project_metrics`: recomputes `Project.avg_score` and `score_distribution` for modified projects (every hour)
- Anonymization function: erases `delivery_target_hash`, reduces `economic_summary` to buckets, simplifies `criterion_evaluations`, preserves finding counts without content
- Initial catalog loading: rubric criteria, economic benchmarks, legal corpus (delegated to F3 for corpus, but the table is managed by F8)
- Backups, replication, and disaster recovery plan (configuration, not detailed implementation in the PRD)
- Observability: database health metrics, age of last executed jobs, record counts by table and state

**Out of scope:**

- Text extraction logic (F1)
- Contract classification logic (F2)
- Semantic corpus search (F3)
- Rubric application (F4)
- Economic computations (F5)
- Report generation (F6)
- Report delivery (F7)
- Admin UI for manual data editing
- Advanced BI tooling (ad-hoc queries are run with a direct SQL client)
- Data migration tooling between product versions

---

## 3. User Stories

### US-01: System initializes the database schema

**As an** operator,
**I want to** execute migrations to create all required tables,
**So that** the system starts clean on a new environment.

**Acceptance criteria:**

- The system uses Django’s built-in migration framework (Django 5.2 LTS) as the migration tool
- Migrations are versioned and committed to the repo
- The command `python manage.py migrate` runs all pending migrations
- The initial schema creates all tables listed in `DOMAIN_MODEL.md` with their indices, constraints, and triggers where applicable
- Migrations are idempotent: running twice does not break anything
- An optional "seed" migration is included that loads initial catalogs (rubric version `1.0.0`, placeholder corpus version, criteria from YAML)
- The system verifies on startup that the current schema matches the code's expected version; if not, it fails with a clear message

---

### US-02: System creates or associates the Project when receiving an analysis

**As the** system,
**I want to** associate each analysis with a Project entity by normalized name,
**So that** aggregate intelligence accumulates without PII leakage.

**Acceptance criteria:**

- F8 exposes function `find_or_create_project(canonical_name, normalized_name) -> Project`
- F2 invokes this function when name extraction finishes
- The function performs an atomic UPSERT over `project`:
  - If `normalized_name` already exists: updates `last_analyzed` and `canonical_name` (if the new one differs, the more recent is preserved)
  - If it does not exist: creates with `first_seen=NOW()`, `total_analyses=0`
- The function returns `project.id` so F2 associates it with `contract_analysis`
- If `normalized_name` is in format `unknown_<short_hash>`, NO matching is performed; always creates new (each analysis with an unknown project is a distinct project)
- Placeholder projects are flagged with `metadata.placeholder=true` so they do not contribute to global aggregate statistics

---

### US-03: System updates aggregate Project metrics

**As the** system,
**I want to** keep Project metrics updated as analyses get associated,
**So that** a user's report shows the correct aggregate context.

**Acceptance criteria:**

- When a `contract_analysis` is completed (all fields populated by F4 and F5), F8 triggers recompute on its `project`
- The recompute updates:
  - `total_analyses`: increment by 1
  - `avg_score`: average of `score_total` of all associated analyses that are NOT anonymized (anonymized ones preserve the score and are included)
  - `score_distribution`: count per band `{green: N, yellow: M, red: K}`
- The recompute is transactional with the analysis insert
- If the recompute fails, the analysis persists but the project metrics are flagged "stale" and the `recompute_project_metrics` cron job corrects them in its next run
- F6 reads `Project.total_analyses` and `Project.avg_score` to display the context in the report

---

### US-04: System runs transient-submission cleanup

**As the** system,
**I want to** delete `contract_submission` and `ocr_job` rows past 24 hours,
**So that** garbage does not accumulate and the database stays compact.

**Acceptance criteria:**

- Cron job `cleanup_transient` runs every 15 minutes
- The job executes:
  ```sql
  DELETE FROM contract_submission WHERE expires_at < NOW();
  -- ON DELETE CASCADE removes associated ocr_job rows automatically
  ```
- If the number of rows to delete exceeds a threshold (10,000), it executes in batches to not block the database
- The job records metrics: rows deleted, execution time, table size post-cleanup
- If the job fails, it retries on the next run; no immediate retry
- The job never deletes rows with `analysis_id IS NOT NULL` and `processing_status != 'completed'` (these are mid-flow and cleanup waits an iteration)

---

### US-05: System erases the encrypted destination after successful delivery

**As the** system,
**I want to** erase `delivery_request.target_value_encrypted` once delivery completes,
**So that** the original email or phone does not remain stored unnecessarily.

**Acceptance criteria:**

- Erasure is F7's immediate responsibility when marking a `DeliveryRequest` as `delivered`
- As a safety net, F8 runs cron job `cleanup_delivery_targets` every 5 minutes:
  ```sql
  UPDATE delivery_request
  SET target_value_encrypted = NULL,
      target_value_encrypted_kms_key_id = NULL
  WHERE status = 'delivered'
    AND target_value_encrypted IS NOT NULL
    AND delivered_at < NOW() - INTERVAL '5 minutes';
  ```
- It also erases `target_value_encrypted` for deliveries that already passed `expires_at` even if not `delivered`:
  ```sql
  UPDATE delivery_request
  SET target_value_encrypted = NULL,
      target_value_encrypted_kms_key_id = NULL
  WHERE expires_at < NOW()
    AND target_value_encrypted IS NOT NULL;
  ```
- `target_hash` is NOT erased; it is preserved until analysis anonymization to allow resends

---

### US-06: System marks expired links

**As the** system,
**I want to** mark `contract_analysis` rows whose `link_expires_at` passed as `expired`,
**So that** the public endpoint stops serving the report.

**Acceptance criteria:**

- Cron job `expire_links` runs every hour
- Executes:
  ```sql
  UPDATE contract_analysis
  SET delivery_status = 'expired'
  WHERE link_expires_at < NOW()
    AND delivery_status NOT IN ('expired', 'failed');
  ```
- The job does NOT delete the `contract_analysis`; only changes state
- F7 verifies state when serving the link and shows the expired page if applicable
- The job records metrics: how many links were marked expired

---

### US-07: System anonymizes analyses at 90 days

**As the** system,
**I want to** anonymize analyses that reach 90 days since creation,
**So that** the privacy promise materializes and the data preserves only the aggregate.

**Acceptance criteria:**

- Cron job `anonymize_old_analyses` runs daily at 03:00 El Salvador time (UTC-6)
- The job batch-processes analyses with `created_at < NOW() - 90 days AND anonymized_at IS NULL`
- For each analysis, the anonymization runs atomically:
  - Erases `delivery_target_hash`
  - Erases `criterion_evaluations` (preserves only counts in `scores_by_category`)
  - Erases `findings` (preserves only `findings_count`, `critical_findings_count`, `unverifiable_count` which are already denormalized)
  - Reduces `economic_summary` to discrete buckets per BR-09
  - Preserves: `score_total`, `band`, `override_triggered`, `scores_by_category` (only the numeric score, not the criterion detail), `submission_hash` (for future idempotency), `contract_type`, `project_id`, `created_at`, `executive_summary`
  - Sets `anonymized_at = NOW()`
- After anonymization, project metrics are NOT recomputed (the analysis's score and band were preserved)
- The job is idempotent: re-running on already-anonymized analyses does nothing
- The job has a pause mechanism: on error, it auto-pauses and emits an operational alert rather than continuing to process potentially corrupted data
- If the job is interrupted mid-batch, the next run resumes from where it left off (the `anonymized_at` field acts as a checkpoint)

---

### US-08: System reduces economic to discrete buckets at anonymization

**As the** system,
**I want to** transform exact economic figures to ranges at anonymization,
**So that** the remaining data contributes to the aggregate without allowing re-identification.

**Acceptance criteria:**

- The function `anonymize_economic_summary(economic_summary) -> economic_summary_bucketed` transforms each numeric field to its bucket
- Defined buckets:
  - `price_cash_bucket`: `<30k`, `30k-60k`, `60k-100k`, `100k-150k`, `150k-250k`, `>250k`
  - `down_payment_pct_bucket`: `0-5`, `5-10`, `10-15`, `15-25`, `25-40`, `>40`
  - `annual_rate_pct_bucket`: `<7`, `7-9`, `9-12`, `12-15`, `15-20`, `>20`
  - `term_months_bucket`: `<120`, `120-180`, `180-240`, `240-300`, `>300`
- The `benchmark_comparisons` are also anonymized: `assessment` and `metric` are preserved, exact values are erased
- The overcost summary is reduced to a qualitative label: `none`, `small`, `medium`, `large`
- The result is persisted replacing the original `economic_summary`
- The field `anonymized: true` is added to the JSONB so F6 knows it must use the anonymized template

---

### US-09: System recomputes project metrics periodically

**As the** system,
**I want to** recompute `Project.avg_score` and `score_distribution` periodically,
**So that** metrics reflect current state even in the face of inconsistencies or anonymizations.

**Acceptance criteria:**

- Cron job `recompute_project_metrics` runs every hour
- The job identifies projects with `last_recomputed_at IS NULL OR last_recomputed_at < last_analyzed`
- For each candidate project, recomputes:
  ```sql
  UPDATE project SET
      avg_score = (SELECT AVG(score_total) FROM contract_analysis WHERE project_id = $1),
      score_distribution = (
          SELECT jsonb_build_object(
              'green', COUNT(*) FILTER (WHERE band = 'green'),
              'yellow', COUNT(*) FILTER (WHERE band = 'yellow'),
              'red', COUNT(*) FILTER (WHERE band = 'red')
          )
          FROM contract_analysis WHERE project_id = $1
      ),
      total_analyses = (SELECT COUNT(*) FROM contract_analysis WHERE project_id = $1),
      last_recomputed_at = NOW()
  WHERE id = $1;
  ```
- The job processes in batches to avoid saturation
- If there are placeholder projects (`metadata.placeholder = true`), they are excluded from the global recompute but keep their individual metrics

---

### US-10: System keeps immutable versioned catalogs

**As the** system,
**I want to** guarantee versioned catalogs (rubric, corpus, benchmarks) do not mutate after publication,
**So that** past analyses can be regenerated exactly.

**Acceptance criteria:**

- The tables `rubric_version`, `corpus_version`, and `benchmark_version` have strict policies:
  - INSERT: allowed via explicit command (not from application code)
  - UPDATE: only allowed on the `is_active` field (to activate or deactivate)
  - DELETE: never allowed
- Dependent tables (`criterion`, `legal_chunk`, `economic_benchmark`) are identified by `(natural_key, version)` where `version` is FK to the versions table
- If a version is deactivated, new analyses do not use it, but existing analyses that reference it continue to function for report regeneration
- The system rejects attempts to modify criteria, legal chunks, or benchmarks of published versions; changes require a new version

---

## 4. Business Rules

**BR-00 (governing invariant):** The full text of the analyzed contract is never persisted in any system table. F1 discards it after extraction. F2, F4, F5 pass it in memory between features. The only ways textual fragments of the contract survive in the database are: (a) the `evidence_clause_snippet` embedded in each `Finding` inside `contract_analysis.findings`, subject to 90-day anonymization, and (b) the economic figures inside `economic_summary`, also subject to anonymization. This invariant is the structural guarantee of the product's privacy promise. Any future feature that requires persisting more contract content must pass through explicit privacy review and update of the general PRD.

**BR-01:** The database schema is owned by F8. Other features can read/write but not alter the structure. Schema changes go through a Django migration with review.

**BR-02:** Persistent tables (`project`, `contract_analysis`, catalogs) have indefinite life or governed by explicit retention policy. Transient ones (`contract_submission`, `ocr_job`, `delivery_request`) are deleted after their TTL.

**BR-03:** The 90-day analysis anonymization is invariant. Configurable by env var only downward (shorten to 60 days yes, lengthen to 120 days requires product approval and privacy review).

**BR-04:** The anonymization job is transactional per analysis. Either an analysis is fully anonymized or not anonymized at all. No partial anonymization.

**BR-05:** Cron jobs must be idempotent. Running them twice causes no harm. This allows resumption after failures without complex coordination.

**BR-06:** The `Project` entity is never deleted. Even if all its analyses are anonymized, the project persists with its aggregate metrics.

**BR-07:** Placeholder projects (`metadata.placeholder=true`) are not reused across submissions. Each submission with an unextractable name creates its own placeholder.

**BR-08:** The computation of `Project.avg_score` includes anonymized analyses (because they preserve `score_total`). It is not a rolling average; it is a simple average of all analyses of the project.

**BR-09:** The anonymization buckets of `economic_summary` are fixed and documented. Changing the buckets requires explicit migration; not done inline.

**BR-10:** The database uses Postgres 15+ with the `pgvector` extension. Installing the extension is infrastructure's responsibility, not application code's.

**BR-11:** Backups: the database is backed up daily with 30-day retention. Backups are encrypted at rest. Backups containing pre-anonymization analyses are not kept beyond 90 days to maintain consistency with the policy.

**BR-12:** Direct database access in production is restricted to operators with multi-factor authentication. Application access is via connection pool with rotating credentials.

**BR-13:** Cron jobs emit metrics on each run: start timestamp, end timestamp, records processed, errors. If a job has not run in N+1 periods (where N is the expected frequency), an alert fires.

**BR-14:** Production schema migrations run in controlled windows with documented rollback plan. Migrations requiring downtime are announced in advance.

**BR-15:** Casa Segura maintains a privacy event log (anonymizations executed, deletions executed, admin accesses) in a `privacy_audit_log` table with 1-year TTL.

---

## 5. Data Models

### 5.1 Complete schema (executable DDL)

Below is the complete DDL of all tables. Order matters (FK dependencies).

```sql
-- =================================
-- Extensions
-- =================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =================================
-- Versioned catalogs
-- =================================

CREATE TABLE rubric_version (
    version TEXT PRIMARY KEY,
    released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    criteria_count INTEGER NOT NULL,
    categories JSONB NOT NULL,
    changelog TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_rubric_version_active ON rubric_version(is_active) WHERE is_active = TRUE;

CREATE TABLE corpus_version (
    version TEXT PRIMARY KEY,
    released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    laws_count INTEGER NOT NULL,
    articles_count INTEGER NOT NULL,
    chunks_count INTEGER NOT NULL,
    manifest JSONB NOT NULL,
    changelog TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_corpus_version_active ON corpus_version(is_active) WHERE is_active = TRUE;

CREATE TABLE benchmark_version (
    version TEXT PRIMARY KEY,
    released_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    benchmark_count INTEGER NOT NULL,
    changelog TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_benchmark_version_active ON benchmark_version(is_active) WHERE is_active = TRUE;

CREATE TABLE criterion (
    id TEXT NOT NULL,
    rubric_version TEXT NOT NULL REFERENCES rubric_version(version),
    category CHAR(1) NOT NULL CHECK (category IN ('A','B','C','D','E','F')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    weight_in_category NUMERIC(4,2) NOT NULL CHECK (weight_in_category > 0 AND weight_in_category <= 100),
    applicable_types TEXT[] NOT NULL,
    legal_anchor TEXT[] NOT NULL DEFAULT '{}',
    override_code TEXT,
    evaluation_prompt TEXT NOT NULL,
    scoring_scale JSONB NOT NULL,
    worst_case_when_unverifiable NUMERIC(3,1) NOT NULL DEFAULT 4.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, rubric_version)
);

CREATE INDEX idx_criterion_rubric_version ON criterion(rubric_version);
CREATE INDEX idx_criterion_category ON criterion(category);
CREATE INDEX idx_criterion_applicable_types ON criterion USING GIN(applicable_types);

CREATE TABLE legal_document (
    law_id TEXT NOT NULL,
    corpus_version TEXT NOT NULL REFERENCES corpus_version(version),
    title TEXT NOT NULL,
    short_title TEXT,
    decree TEXT,
    issued_at DATE,
    official_gazette TEXT,
    status TEXT NOT NULL CHECK (status IN ('in_force', 'repealed', 'in_force_with_amendments')),
    subject TEXT,
    source_url TEXT,
    last_verified DATE NOT NULL,
    relevance_to_casa_segura TEXT CHECK (relevance_to_casa_segura IN ('high', 'medium', 'low')),
    covers TEXT[],
    tags TEXT[],
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (law_id, corpus_version)
);

CREATE INDEX idx_legal_document_corpus_version ON legal_document(corpus_version);

CREATE TABLE legal_chunk (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    corpus_version TEXT NOT NULL REFERENCES corpus_version(version),
    law_id TEXT NOT NULL,
    article_number TEXT NOT NULL,
    anchor TEXT NOT NULL,
    text_paraphrased TEXT NOT NULL,
    text_verbatim TEXT,
    embedding VECTOR(384) NOT NULL,
    tags TEXT[] NOT NULL DEFAULT '{}',
    relevance_for_findings TEXT[] NOT NULL DEFAULT '{}',
    severity_hint TEXT CHECK (severity_hint IN ('override_critical', 'red', 'yellow', 'green') OR severity_hint IS NULL),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (law_id, corpus_version) REFERENCES legal_document(law_id, corpus_version) ON DELETE CASCADE,
    UNIQUE (corpus_version, law_id, anchor)
);

CREATE INDEX idx_legal_chunk_corpus_version ON legal_chunk(corpus_version);
CREATE INDEX idx_legal_chunk_law_id ON legal_chunk(law_id);
CREATE INDEX idx_legal_chunk_tags ON legal_chunk USING GIN(tags);
CREATE INDEX idx_legal_chunk_relevance ON legal_chunk USING GIN(relevance_for_findings);
CREATE INDEX idx_legal_chunk_embedding ON legal_chunk USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

CREATE TABLE economic_benchmark (
    benchmark_key TEXT NOT NULL,
    benchmark_version TEXT NOT NULL REFERENCES benchmark_version(version),
    value_min NUMERIC(10,4),
    value_max NUMERIC(10,4),
    value_default NUMERIC(10,4),
    unit TEXT NOT NULL CHECK (unit IN ('pct', 'usd', 'months', 'multiplier', 'ratio')),
    applicable_contract_types TEXT[] NOT NULL,
    source TEXT NOT NULL,
    source_url TEXT,
    last_updated DATE NOT NULL,
    next_review_due DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (benchmark_key, benchmark_version)
);

CREATE INDEX idx_benchmark_version ON economic_benchmark(benchmark_version);
CREATE INDEX idx_benchmark_types ON economic_benchmark USING GIN(applicable_contract_types);

-- =================================
-- Primary business entities
-- =================================

CREATE TABLE project (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL UNIQUE,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_analyzed TIMESTAMPTZ NOT NULL,
    last_recomputed_at TIMESTAMPTZ,
    total_analyses INTEGER NOT NULL DEFAULT 0,
    avg_score NUMERIC(3,1),
    score_distribution JSONB DEFAULT '{"green": 0, "yellow": 0, "red": 0}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_project_normalized ON project(normalized_name);
CREATE INDEX idx_project_last_analyzed ON project(last_analyzed);

CREATE TABLE contract_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    public_short_id TEXT NOT NULL UNIQUE,
    project_id UUID NOT NULL REFERENCES project(id),
    submission_hash TEXT NOT NULL,

    -- Classification
    contract_type TEXT NOT NULL,
    contract_type_declared TEXT,
    contract_type_reclassified BOOLEAN NOT NULL DEFAULT FALSE,
    reclassification_reason TEXT,
    reclassification_indicators JSONB,
    classification_confidence NUMERIC(3,2),
    classification_attempts INTEGER DEFAULT 1,
    elements_detected JSONB,

    -- Analysis result
    score_total NUMERIC(3,1) CHECK (score_total >= 0 AND score_total <= 10),
    band TEXT CHECK (band IN ('green', 'yellow', 'red', 'not_analyzable')),
    override_triggered TEXT[],
    scores_by_category JSONB,
    criterion_evaluations JSONB,
    findings JSONB,
    findings_count INTEGER DEFAULT 0,
    critical_findings_count INTEGER DEFAULT 0,
    unverifiable_count INTEGER DEFAULT 0,
    executive_summary TEXT,
    economic_summary JSONB,

    -- Versioning
    rubric_version TEXT REFERENCES rubric_version(version),
    corpus_version TEXT REFERENCES corpus_version(version),
    benchmark_version TEXT REFERENCES benchmark_version(version),

    -- Delivery state
    delivery_status TEXT NOT NULL DEFAULT 'pending' CHECK (
        delivery_status IN ('pending', 'queued', 'sent_sms', 'sent_email', 'available_link', 'expired', 'failed')
    ),
    delivery_channel TEXT CHECK (delivery_channel IN ('sms_summary', 'email_pdf', 'web_link')),
    delivery_target_hash TEXT,
    link_expires_at TIMESTAMPTZ,
    resend_count INTEGER NOT NULL DEFAULT 0,

    -- Anonymization
    anonymized_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_analysis_project ON contract_analysis(project_id);
CREATE INDEX idx_analysis_public_short_id ON contract_analysis(public_short_id);
CREATE INDEX idx_analysis_submission_hash ON contract_analysis(submission_hash);
CREATE INDEX idx_analysis_link_expires_at ON contract_analysis(link_expires_at) WHERE link_expires_at IS NOT NULL;
CREATE INDEX idx_analysis_anonymized_at ON contract_analysis(anonymized_at) WHERE anonymized_at IS NULL;
CREATE INDEX idx_analysis_created_at ON contract_analysis(created_at);

-- =================================
-- Transient entities
-- =================================

CREATE TABLE contract_submission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_hash TEXT NOT NULL,
    public_short_id TEXT NOT NULL UNIQUE,
    file_count INTEGER NOT NULL CHECK (file_count >= 1 AND file_count <= 50),
    total_size_bytes BIGINT NOT NULL,
    total_pages INTEGER,
    file_formats TEXT[] NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('web')),
    source_metadata JSONB DEFAULT '{}'::jsonb,
    processing_status TEXT NOT NULL CHECK (processing_status IN (
        'received', 'extracting', 'extracted', 'classifying', 'analyzing',
        'completed', 'failed_extraction', 'failed_classification', 'failed_analysis',
        'rejected_language', 'rejected_type', 'rejected_size', 'expired'
    )),
    extraction_strategy_attempted TEXT,
    extraction_strategy_successful TEXT,
    extracted_text_token_count INTEGER,
    extracted_text_language TEXT,
    extracted_text_language_confidence NUMERIC(3,2),
    error_code TEXT,
    error_reason TEXT,
    analysis_id UUID REFERENCES contract_analysis(id),
    disclaimer_accepted_at TIMESTAMPTZ NOT NULL,
    disclaimer_accepted_via TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX idx_submission_hash ON contract_submission(submission_hash);
CREATE INDEX idx_submission_status ON contract_submission(processing_status);
CREATE INDEX idx_submission_expires ON contract_submission(expires_at);
CREATE INDEX idx_submission_analysis ON contract_submission(analysis_id) WHERE analysis_id IS NOT NULL;

CREATE TABLE ocr_job (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES contract_submission(id) ON DELETE CASCADE,
    strategy TEXT NOT NULL CHECK (strategy IN ('pypdf', 'vision_llm', 'tesseract')),
    attempt_number INTEGER NOT NULL DEFAULT 1,
    model_used TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed', 'timeout', 'cancelled')),
    pages_processed INTEGER,
    pages_failed INTEGER,
    tokens_consumed INTEGER,
    cost_estimate_cents INTEGER,
    average_confidence NUMERIC(4,2),
    error_code TEXT,
    error_message TEXT,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours')
);

CREATE INDEX idx_ocr_job_submission ON ocr_job(submission_id);
CREATE INDEX idx_ocr_job_status ON ocr_job(status);
CREATE INDEX idx_ocr_job_expires ON ocr_job(expires_at);

CREATE TABLE delivery_request (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES contract_analysis(id) ON DELETE CASCADE,
    channel TEXT NOT NULL CHECK (channel IN ('sms_summary', 'email_pdf', 'web_link')),
    target_hash TEXT,
    target_value_encrypted TEXT,
    target_value_encrypted_kms_key_id TEXT,
    is_resend BOOLEAN NOT NULL DEFAULT FALSE,
    parent_delivery_request_id UUID REFERENCES delivery_request(id),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at TIMESTAMPTZ,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    next_attempt_not_before TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('queued', 'sending', 'delivered', 'failed', 'expired')),
    last_error_code TEXT,
    last_error_message TEXT,
    last_error_classification TEXT CHECK (last_error_classification IN ('transient', 'permanent')),
    provider_message_id TEXT,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days')
);

CREATE INDEX idx_delivery_analysis ON delivery_request(analysis_id);
CREATE INDEX idx_delivery_status ON delivery_request(status);
CREATE INDEX idx_delivery_next_attempt ON delivery_request(next_attempt_not_before) WHERE status = 'queued';
CREATE INDEX idx_delivery_expires ON delivery_request(expires_at);

-- =================================
-- Audit
-- =================================

CREATE TABLE privacy_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'analysis_anonymized', 'delivery_target_purged', 'submission_purged',
        'manual_data_deletion', 'admin_access', 'corpus_version_published',
        'rubric_version_published'
    )),
    related_id UUID,
    related_table TEXT,
    event_data JSONB,
    triggered_by TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '1 year')
);

CREATE INDEX idx_audit_event_type ON privacy_audit_log(event_type);
CREATE INDEX idx_audit_occurred_at ON privacy_audit_log(occurred_at);
CREATE INDEX idx_audit_expires ON privacy_audit_log(expires_at);

-- =================================
-- Observability
-- =================================

CREATE TABLE job_execution_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_name TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    records_processed INTEGER,
    error_message TEXT,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '30 days')
);

CREATE INDEX idx_job_log_name ON job_execution_log(job_name);
CREATE INDEX idx_job_log_started ON job_execution_log(started_at);
CREATE INDEX idx_job_log_expires ON job_execution_log(expires_at);
```

### 5.2 Views for observability

```sql
-- System health in a single query
CREATE VIEW v_system_health AS
SELECT
    (SELECT COUNT(*) FROM contract_submission WHERE processing_status = 'received') AS submissions_pending,
    (SELECT COUNT(*) FROM contract_submission WHERE processing_status LIKE 'failed_%') AS submissions_failed_last_24h,
    (SELECT COUNT(*) FROM contract_analysis WHERE created_at > NOW() - INTERVAL '24 hours') AS analyses_last_24h,
    (SELECT COUNT(*) FROM contract_analysis WHERE anonymized_at IS NULL AND created_at < NOW() - INTERVAL '90 days') AS analyses_pending_anonymization,
    (SELECT COUNT(*) FROM delivery_request WHERE status = 'queued') AS deliveries_queued,
    (SELECT COUNT(*) FROM delivery_request WHERE status = 'failed' AND requested_at > NOW() - INTERVAL '24 hours') AS deliveries_failed_last_24h,
    (SELECT MAX(occurred_at) FROM privacy_audit_log WHERE event_type = 'analysis_anonymized') AS last_anonymization_run,
    (SELECT COUNT(*) FROM project) AS total_projects,
    (SELECT MAX(version) FROM rubric_version WHERE is_active = TRUE) AS active_rubric_version,
    (SELECT MAX(version) FROM corpus_version WHERE is_active = TRUE) AS active_corpus_version,
    (SELECT MAX(version) FROM benchmark_version WHERE is_active = TRUE) AS active_benchmark_version;

-- Retention metrics
CREATE VIEW v_retention_status AS
SELECT
    'contract_submission' AS table_name,
    COUNT(*) FILTER (WHERE expires_at < NOW()) AS overdue_records,
    COUNT(*) AS total_records
FROM contract_submission
UNION ALL
SELECT 'ocr_job', COUNT(*) FILTER (WHERE expires_at < NOW()), COUNT(*) FROM ocr_job
UNION ALL
SELECT 'delivery_request', COUNT(*) FILTER (WHERE expires_at < NOW()), COUNT(*) FROM delivery_request
UNION ALL
SELECT 'contract_analysis (pending anon)', COUNT(*) FILTER (WHERE created_at < NOW() - INTERVAL '90 days' AND anonymized_at IS NULL), COUNT(*) FROM contract_analysis;
```

---

## 6. Integration Points

### 6.1 Consumed by all other features

F8 is the database. Each feature reads and writes the corresponding tables per `FEATURES_MAP.md` §4.

### 6.2 Cron jobs

The jobs run in a separate process from the API. Recommendation: `apscheduler` integrated into the service, or operating-system cron invoking `python -m casa_segura.jobs.<job_name>`.

| Job | Frequency | Expected duration |
|---|---|---|
| `cleanup_transient` | every 15 min | < 5s typical |
| `cleanup_delivery_targets` | every 5 min | < 2s |
| `expire_links` | every hour | < 1s |
| `anonymize_old_analyses` | daily 03:00 | several minutes |
| `recompute_project_metrics` | every hour | < 10s |
| `audit_log_cleanup` | weekly | < 30s |

### 6.3 Configuration

- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` env vars
- `DB_POOL_MIN_SIZE` (default 5)
- `DB_POOL_MAX_SIZE` (default 20)
- `ANONYMIZATION_AFTER_DAYS` (default 90)
- `JOB_BATCH_SIZE` (default 1000)
- `JOB_TIMEZONE` (default `America/El_Salvador`)

### 6.4 Backup and disaster recovery

- Daily full backups + WAL streaming to offsite storage
- Backup retention: 30 days, with special care to not preserve pre-anonymization data beyond the policy
- Restore procedure documented in operational runbook
- Quarterly restore drills

---

## 7. API Surface

F8 does not expose public HTTP endpoints. It is data layer and batch processes.

Internal endpoints for operators are exposed:

### 7.1 `GET /v1/internal/health/db` (requires `X-Internal-Auth`)

Returns the contents of `v_system_health`.

### 7.2 `POST /v1/internal/jobs/trigger/{job_name}` (requires `X-Internal-Auth`)

Allows manually triggering a job.

### 7.3 `GET /v1/internal/audit/anonymization-log` (requires `X-Internal-Auth`)

Returns recent anonymization events for audit.

---

## 8. LLM Prompts

F8 does not use an LLM.

---

## 9. Non-Functional Requirements

- **P50 latency for primary queries:** under 20 ms (lookup by `public_short_id`, project lookup by `normalized_name`).
- **P95 latency:** under 100 ms.
- **Throughput:** support at least 500 queries per second in typical mix (read + write).
- **Database availability:** over 99.9%.
- **RPO (recovery point objective):** under 1 hour (WAL streaming).
- **RTO (recovery time objective):** under 4 hours for full restore from backup.
- **Anonymization job:** must complete in under 30 minutes to process the typical daily batch (1000-5000 analyses).
- **Transient cleanup job:** must complete in under 5 minutes per cycle.
- **Expected database size at steady state:** 10-50 GB in the first year, with growth dominated by `legal_chunk` (corpus) and `contract_analysis` (aggregate data).
- **Encryption at rest:** enabled at disk level via the infrastructure provider.
- **Application-level encryption of sensitive data:** `target_value_encrypted` with KMS per F7.
- **Observability:** Prometheus DB-health metrics (active connections, query latency, locks, table sizes), alerts on jobs not executed, pending anonymizations, migration errors.

---

## 10. Open Questions

1. Is the database self-hosted Postgres or managed (RDS, Cloud SQL, Supabase)? Managed reduces operational effort but monthly costs are significant. Self-hosted with HA requires expertise. Product must decide.

2. Is the KMS for `target_value_encrypted` from the cloud provider or open source (HashiCorp Vault)? Affects vendor lock-in.

3. Should anonymization be triggerable on user request before 90 days (cancellation right per LPC and data protection regulation)? My recommendation: yes, via endpoint with hash verification.

4. Should backups be encrypted with a key the system operator does not possess, to protect against internal access? Overkill for MVP but important for a production version.

5. How are placeholder projects handled long term? Each is a unique project per submission. Over time, we could have thousands of placeholder projects. Do they have value or are they deleted after all their analyses anonymize?

6. Should `submission_hash` survive anonymization for future idempotency? My proposal: yes; a content hash is not PII. Allows a user who re-uploads the same contract two years later to receive "we already analyzed this contract a while back, here is the anonymized version".

7. Do schema migrations require planned downtime? Some operations (adding a NOT NULL column to a large table) are blocking. Product must define acceptable maintenance windows.

8. Should the `privacy_audit_log` table have access restricted to a subset of operators (a "compliance officer" role)? Broad access dilutes its value as an audit trail.

9. Should corpus, rubric, and benchmark versions be published via approved PR, or can any operator with DB access insert them? My proposal: PR with CI that validates consistency before applying the migration to production.

10. Is a `system_config` table needed for parameters that change without code (link TTLs, RAG threshold, etc.)? Today everything is in env vars. A table allows hot changes without redeploy, but introduces another change surface.

---

**End of document.**
