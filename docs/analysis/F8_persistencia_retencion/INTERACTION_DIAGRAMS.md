# Interaction Diagrams — F8: Persistence, Project Entity & Retention

> Generated: 2026-05-15

---

## Component Overview

```mermaid
graph TD
    Beat[Celery Beat]
    Tasks[Periodic cleanup tasks]
    RetSvc[RetentionService]
    ProjSvc[ProjectService]
    Repos[Repositories]
    PG[(Postgres)]
    OtherFeats[F1-F7 features]

    OtherFeats --> Repos
    Beat --> Tasks --> RetSvc --> Repos --> PG
    RetSvc --> ProjSvc --> Repos
```

---

## Flow: US-01 Schema initialization

```mermaid
sequenceDiagram
    actor Op as Operator
    participant Mgmt as Django management
    participant Alembic as Django migrate
    participant PG as Postgres

    Op->>Mgmt: python manage.py migrate
    Mgmt->>PG: CREATE EXTENSION pgcrypto, uuid-ossp, vector
    Mgmt->>PG: platform.0001_initial.py creates project, contract_analysis, privacy_audit_log, job_execution_log
    Mgmt->>PG: platform.0002_seed.py INSERT placeholder project, default rubric/corpus/benchmark versions
    Mgmt->>PG: corpus.0001_initial.py creates corpus_version, legal_document, legal_chunk, rag_query_log (with HNSW)
    Mgmt->>PG: rubric.0001_initial.py creates rubric_version, criterion
    Mgmt->>PG: rubric.0002_seed_v1_0_0.py inserts the 38 criteria from YAML
    Mgmt->>PG: economics.0001_initial.py creates benchmark_version, economic_benchmark
    Mgmt->>PG: economics.0002_seed_2026_Q2.py inserts benchmarks
    Mgmt->>PG: ingestion.0001_initial.py (no-op; tables owned by platform)
    Mgmt->>PG: classification.0001_initial.py creates classification_job
    Mgmt->>PG: reports.0001_initial.py creates report_generation_log
    Mgmt->>PG: delivery.0001_initial.py creates delivery_request
    Mgmt->>PG: delivery.0002_audit_view.py creates v_delivery_audit
    Mgmt-->>Op: schema ready
```

---

## Flow: US-02 Find or create Project

```mermaid
sequenceDiagram
    participant F2 as F2 ClassificationService
    participant Svc as ProjectService
    participant Repo as ProjectRepository
    participant PG as Postgres

    F2->>Svc: find_or_create("Residencial Las Palmeras","las palmeras")
    Svc->>Repo: upsert(canonical, normalized)
    Repo->>PG: INSERT ... ON CONFLICT (normalized_name) DO UPDATE SET last_analyzed=NOW(), canonical_name=EXCLUDED.canonical_name RETURNING id, (xmax = 0) AS was_inserted
    PG-->>Repo: project_id, was_inserted
    Repo-->>Svc: Project
    Svc-->>F2: Project
    Note over Svc: total_analyses NOT incremented inline; the hourly cron does it
```

---

## Flow: US-03 Update aggregate metrics

```mermaid
sequenceDiagram
    participant Beat as Celery Beat hourly
    participant Task as RecomputeProjectMetricsTask
    participant Svc as ProjectService
    participant Repo as ProjectRepository
    participant PG as Postgres

    Beat->>Task: recompute_project_metrics.delay()
    Task->>Svc: recompute_all_due()
    Svc->>Repo: list_due()
    Repo->>PG: SELECT id FROM project WHERE COALESCE(last_recomputed_at, 'epoch') < last_analyzed AND NOT (metadata ? 'placeholder' AND metadata->>'placeholder' = 'true')
    PG-->>Repo: ids
    loop per project
        Svc->>Repo: recompute(id)
        Repo->>PG: UPDATE project SET avg_score=(SELECT AVG(score_total) FROM contract_analysis WHERE project_id=$1), score_distribution=(SELECT jsonb_build_object('green', COUNT(*) FILTER (WHERE band='green'), 'yellow', COUNT(*) FILTER (WHERE band='yellow'), 'red', COUNT(*) FILTER (WHERE band='red')) FROM contract_analysis WHERE project_id=$1), total_analyses=(SELECT COUNT(*) FROM contract_analysis WHERE project_id=$1), last_recomputed_at=NOW() WHERE id=$1
        PG-->>Repo: ok
    end
    Svc-->>Task: {recomputed: N}
```

---

## Flow: US-04 cleanup_transient (every 15 min)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant Task as CleanupTransientTask
    participant Svc as RetentionService
    participant PG as Postgres
    participant Audit as PrivacyAuditLogRepository

    Beat->>Task: cleanup_transient.delay()
    Task->>Svc: cleanup_transient()
    Svc->>PG: DELETE FROM contract_submission WHERE expires_at < NOW() AND processing_status NOT IN ('received','extracting','classifying','analyzing') LIMIT 10000
    PG-->>Svc: N (cascades delete to ocr_job)
    Svc->>Audit: write(event_type='submission_purged', event_data={count:N})
    Svc-->>Task: {deleted: N}
```

---

## Flow: US-05 cleanup_delivery_targets (every 5 min)

Per F7 Flow 8 — same as documented there.

---

## Flow: US-06 expire_links (hourly)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat hourly
    participant Task as ExpireLinksTask
    participant Svc as RetentionService
    participant PG as Postgres

    Beat->>Task: expire_links.delay()
    Task->>Svc: expire_links()
    Svc->>PG: UPDATE contract_analysis SET delivery_status='expired' WHERE link_expires_at < NOW() AND delivery_status NOT IN ('expired','failed')
    PG-->>Svc: N
    Svc-->>Task: {marked_expired: N}
```

---

## Flow: US-07 anonymize_old_analyses (daily 03:00)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat 03:00 America/El_Salvador
    participant Task as AnonymizeOldAnalysesTask
    participant Svc as RetentionService
    participant AR as ContractAnalysisRepository
    participant Buck as AnonymizationBucketizer
    participant Audit as PrivacyAuditLogRepository
    participant PG as Postgres

    Beat->>Task: anonymize_old_analyses.delay(batch_size=200)
    Task->>Svc: anonymize_old_analyses(batch_size=200)
    Svc->>AR: list_pending_anonymization(cutoff=NOW()-90d, batch=200)
    AR-->>Svc: list[Row]
    loop per row
        Svc->>Buck: bucketize(row.economic_summary)
        Buck-->>Svc: bucketed
        Svc->>AR: anonymize_one(row.id, bucketed)
        AR->>PG: UPDATE contract_analysis SET delivery_target_hash=NULL, criterion_evaluations=NULL, findings=NULL, economic_summary=$bucketed, anonymized_at=NOW() WHERE id=$1
        Svc->>Audit: write(event_type='analysis_anonymized', related_id=row.id, event_data={'rubric_version':...,'corpus_version':...,'benchmark_version':...})
    end
    Svc-->>Task: {anonymized: 200, has_more: bool}
    Note over Task: if has_more, Task can self-rechain with delay
```

---

## Flow: US-08 Bucketization function

```mermaid
sequenceDiagram
    participant Buck as AnonymizationBucketizer

    Note over Buck: price_bucket(80000) → "60k-100k"<br/>down_payment_pct_bucket(0.10) → "10-15"<br/>annual_rate_pct_bucket(0.18) → "15-20"<br/>term_months_bucket(240) → "240-300"<br/>overcost_label(95000) → "large"
```

Bucket definitions (PRD F8 §US-08):
- `price_cash`: `<30k`, `30k-60k`, `60k-100k`, `100k-150k`, `150k-250k`, `>250k`
- `down_payment_pct`: `0-5`, `5-10`, `10-15`, `15-25`, `25-40`, `>40`
- `annual_rate_pct`: `<7`, `7-9`, `9-12`, `12-15`, `15-20`, `>20`
- `term_months`: `<120`, `120-180`, `180-240`, `240-300`, `>300`
- `overcost_label`: `none` (≤ 0), `small` (≤ $10k), `medium` (≤ $50k), `large` (> $50k)

---

## Flow: US-09 audit_log_cleanup (weekly)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat weekly
    participant Task as AuditLogCleanupTask
    participant Svc as RetentionService
    participant PG as Postgres

    Beat->>Task: audit_log_cleanup.delay()
    Task->>Svc: audit_log_cleanup()
    Svc->>PG: DELETE FROM privacy_audit_log WHERE expires_at < NOW() LIMIT 100000
    Svc->>PG: DELETE FROM job_execution_log WHERE expires_at < NOW()
    Svc->>PG: DELETE FROM rag_query_log WHERE expires_at < NOW()
    Svc->>PG: DELETE FROM classification_job WHERE expires_at < NOW()
    Svc->>PG: DELETE FROM report_generation_log WHERE expires_at < NOW()
    Svc-->>Task: {deleted_per_table: {...}}
```

---

## Flow: US-10 Versioned catalogs immutability

```mermaid
sequenceDiagram
    actor Op as Operator
    participant Mgmt as Mgmt command (rubric_seed, corpus_ingest, benchmarks_load)
    participant PG as Postgres

    Op->>Mgmt: insert a new version
    Mgmt->>PG: INSERT INTO rubric_version (...)
    PG-->>Mgmt: ok
    Note over Mgmt: Update only on `is_active`; UPDATE on any other column is rejected via trigger
```

The trigger:

```sql
CREATE OR REPLACE FUNCTION reject_catalog_mutation() RETURNS trigger AS $$
BEGIN
    IF (OLD.version IS NOT DISTINCT FROM NEW.version) AND TG_OP = 'UPDATE' THEN
        IF row_to_json(OLD)::jsonb - 'is_active' IS DISTINCT FROM row_to_json(NEW)::jsonb - 'is_active' THEN
            RAISE EXCEPTION 'Versioned catalog row is immutable except for is_active';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_rubric_version_immutable BEFORE UPDATE ON rubric_version FOR EACH ROW EXECUTE FUNCTION reject_catalog_mutation();
-- analogous triggers for corpus_version, benchmark_version
```

---

## Class Diagram

```mermaid
classDiagram
    class ProjectService
    class RetentionService
    class AnonymizationBucketizer
    class JobRunner
    class ProjectRepository
    class ContractAnalysisRepository
    class PrivacyAuditLogRepository
    class JobExecutionLogRepository
    class CleanupTransientTask
    class CleanupDeliveryTargetsTask
    class ExpireLinksTask
    class AnonymizeOldAnalysesTask
    class RecomputeProjectMetricsTask
    class AuditLogCleanupTask
    class HealthView
    class TriggerJobView
    class AuditLogView

    RetentionService *-- AnonymizationBucketizer
    RetentionService *-- JobRunner
    RetentionService o-- ContractAnalysisRepository
    RetentionService o-- PrivacyAuditLogRepository
    ProjectService o-- ProjectRepository
    AnonymizeOldAnalysesTask ..> RetentionService
    CleanupTransientTask ..> RetentionService
    CleanupDeliveryTargetsTask ..> RetentionService
    ExpireLinksTask ..> RetentionService
    RecomputeProjectMetricsTask ..> ProjectService
    AuditLogCleanupTask ..> RetentionService
    HealthView ..> ContractAnalysisRepository
    TriggerJobView ..> RetentionService
    AuditLogView ..> PrivacyAuditLogRepository
```

**End of document.**
