# Solution Diagrams — F8: Persistence, Project Entity & Retention

> Generated: 2026-05-15

---

## 1. Class Diagram

### 1.1 Domain + Application

```mermaid
classDiagram
    class Project { <<Pydantic>> }
    class ContractAnalysis { <<Pydantic>> }
    class PrivacyAuditLog { <<Pydantic>> }
    class JobExecutionLog { <<Pydantic>> }
    class FindOrCreateProject { <<Command>> }
    class RecomputeProjectMetrics { <<Command>> }
    class AnonymizeAnalysis { <<Command>> }
    class WritePrivacyAuditLog { <<Command>> }
    class WriteJobExecutionLog { <<Command>> }
    class GetSystemHealth { <<Query>> }
    class GetProjectByNormalizedName { <<Query>> }
    class GetAnalysesPendingAnonymization { <<Query>> }
    class ProjectService {
        -ProjectRepository repo
        +find_or_create(canonical, normalized) Project
        +recompute_metrics(project_id) Project
    }
    class RetentionService {
        -ContractSubmissionRepository submission_repo
        -OcrJobRepository ocr_repo
        -DeliveryRequestRepository delivery_repo
        -ContractAnalysisRepository analysis_repo
        -ProjectRepository project_repo
        -PrivacyAuditLogRepository audit_repo
        +cleanup_transient() dict
        +cleanup_delivery_targets() dict
        +expire_links() dict
        +anonymize_old_analyses(batch_size) dict
        +recompute_project_metrics() dict
        +audit_log_cleanup() dict
        -anonymize_one(analysis_id) None
        -bucketize_economic(summary) AnonymizedSummary
    }
    class AnonymizationBucketizer {
        +price_bucket(value) str
        +down_payment_bucket(pct) str
        +rate_bucket(pct) str
        +term_bucket(months) str
        +overcost_label(usd) str
    }
    class JobRunner {
        -JobExecutionLogRepository repo
        +run(job_name, fn) JobExecutionLog
    }
    RetentionService *-- AnonymizationBucketizer
    RetentionService *-- JobRunner
    ProjectService o-- ProjectRepository
```

### 1.2 Infrastructure

```mermaid
classDiagram
    class ProjectModel { <<Django Model>> }
    class ContractAnalysisModel { <<Django Model>> }
    class PrivacyAuditLogModel { <<Django Model>> }
    class JobExecutionLogModel { <<Django Model>> }
    class ProjectRepository { <<DjangoFullRepository>> +upsert(c, n) Project +list_recently_active() list }
    class ContractAnalysisRepository {
        <<DjangoFullRepository>>
        +get_by_public_short_id(short_id) ContractAnalysis
        +list_pending_anonymization(cutoff, batch) list
        +anonymize_one(id, bucketed_economic) None
    }
    class PrivacyAuditLogRepository { <<DjangoFullRepository>> }
    class JobExecutionLogRepository { <<DjangoFullRepository>> }
    class CleanupTransientTask { <<Celery shared_task>> }
    class CleanupDeliveryTargetsTask { <<Celery shared_task>> }
    class ExpireLinksTask { <<Celery shared_task>> }
    class AnonymizeOldAnalysesTask { <<Celery shared_task>> }
    class RecomputeProjectMetricsTask { <<Celery shared_task>> }
    class AuditLogCleanupTask { <<Celery shared_task>> }
    class HealthView { <<DRF APIView>> }
    class TriggerJobView { <<DRF APIView>> }
    class AuditLogView { <<DRF APIView>> }
    ProjectRepository ..> ProjectModel
    ContractAnalysisRepository ..> ContractAnalysisModel
    PrivacyAuditLogRepository ..> PrivacyAuditLogModel
    JobExecutionLogRepository ..> JobExecutionLogModel
    AnonymizeOldAnalysesTask ..> RetentionService
    CleanupTransientTask ..> RetentionService
    HealthView ..> ContractAnalysisRepository
    TriggerJobView ..> RetentionService
```

---

## 2. Sequence Diagrams

### 2.1 Project upsert from F2

```mermaid
sequenceDiagram
    participant F2 as F2 ClassificationService
    participant Svc as ProjectService
    participant Repo as ProjectRepository
    participant PG as Postgres

    F2->>Svc: find_or_create("Residencial Las Palmeras","las palmeras")
    Svc->>Repo: upsert("Residencial Las Palmeras","las palmeras")
    Repo->>PG: INSERT INTO project (...) ON CONFLICT (normalized_name) DO UPDATE SET last_analyzed=NOW(), canonical_name=EXCLUDED.canonical_name RETURNING id, (xmax = 0) AS was_inserted
    PG-->>Repo: project_id
    Repo-->>Svc: Project
    Svc-->>F2: Project
```

### 2.2 Anonymization (daily)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat 03:00
    participant Task as AnonymizeOldAnalysesTask
    participant Svc as RetentionService
    participant Repo as ContractAnalysisRepository
    participant Audit as PrivacyAuditLogRepository
    participant PG as Postgres

    Beat->>Task: anonymize_old_analyses.delay(batch_size=200)
    Task->>Svc: anonymize_old_analyses(200)
    Svc->>Repo: list_pending_anonymization(NOW()-90d, 200)
    Repo-->>Svc: list[ContractAnalysis]
    loop per analysis
        Svc->>Svc: bucketize_economic(summary)
        Svc->>Repo: anonymize_one(id, bucketed, NULL targets, NULL findings details)
        Repo->>PG: UPDATE contract_analysis SET delivery_target_hash=NULL, criterion_evaluations=NULL, findings=NULL, economic_summary=bucketed, anonymized_at=NOW() WHERE id=...
        Svc->>Audit: write(event_type='analysis_anonymized', related_id=id)
    end
    Svc-->>Task: {anonymized: 200}
```

### 2.3 Transient cleanup (every 15 min)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant Task as CleanupTransientTask
    participant Svc as RetentionService
    participant PG as Postgres

    Beat->>Task: cleanup_transient.delay()
    Task->>Svc: cleanup_transient()
    Svc->>PG: DELETE FROM contract_submission WHERE expires_at < NOW() AND processing_status NOT IN ('received','extracting','classifying') LIMIT 10000
    Note over PG: ON DELETE CASCADE removes ocr_job rows
    PG-->>Svc: N rows
    Svc-->>Task: {deleted: N}
```

### 2.4 Recompute project metrics (hourly)

```mermaid
sequenceDiagram
    participant Beat as Celery Beat
    participant Task as RecomputeProjectMetricsTask
    participant Svc as ProjectService
    participant Repo as ProjectRepository
    participant PG as Postgres

    Beat->>Task: recompute_project_metrics.delay()
    Task->>Svc: recompute_all_due()
    Svc->>Repo: list_due()
    Repo->>PG: SELECT id FROM project WHERE last_recomputed_at IS NULL OR last_recomputed_at < last_analyzed
    PG-->>Repo: ids
    loop per project (excluding placeholders)
        Svc->>Repo: recompute(id)
        Repo->>PG: UPDATE project SET avg_score=..., score_distribution=..., total_analyses=..., last_recomputed_at=NOW() WHERE id=...
    end
    Svc-->>Task: {recomputed: N}
```

### 2.5 System health view

```mermaid
sequenceDiagram
    actor Op as Operator
    participant V as HealthView
    participant PG as Postgres

    Op->>V: GET /v1/internal/health/db (X-Internal-Auth)
    V->>PG: SELECT * FROM v_system_health
    PG-->>V: row
    V-->>Op: JSON
```

---

## 3. State Diagram (ContractAnalysis lifecycle from retention perspective)

```mermaid
stateDiagram-v2
    [*] --> active: created
    active --> delivered: F7 delivered
    active --> link_expired: link_expires_at < NOW
    delivered --> link_expired: link_expires_at < NOW
    active --> anonymized: 90 days
    delivered --> anonymized: 90 days
    link_expired --> anonymized: 90 days
    anonymized --> [*]: kept indefinitely
```

---

## 4. Activity Diagram — Anonymize one analysis

```mermaid
flowchart TD
    A[Pick analysis_id] --> B[Read row]
    B --> C[Bucketize economic_summary]
    C --> D[Erase delivery_target_hash]
    D --> E[Erase findings content keep counts]
    E --> F[Erase criterion_evaluations]
    F --> G[Write back UPDATE with anonymized_at=NOW]
    G --> H[Write privacy_audit_log analysis_anonymized]
    H --> Z[End]
```

---

## 5. Component Diagram

```mermaid
graph TD
    Beat[Celery Beat]
    Tasks[Periodic tasks: cleanup_transient, cleanup_delivery_targets, expire_links, anonymize_old_analyses, recompute_project_metrics, audit_log_cleanup, cleanup_*]
    Svc1[RetentionService]
    Svc2[ProjectService]
    Repos[Repositories: Project, ContractAnalysis, PrivacyAuditLog, JobExecutionLog]
    PG[(Postgres)]
    Health[HealthView]
    Trigger[TriggerJobView]
    AuditView[AuditLogView]

    Beat --> Tasks --> Svc1 --> Repos --> PG
    Svc1 --> Svc2 --> Repos
    Health --> PG
    Trigger --> Svc1
    AuditView --> Repos
```

---

## 6. Use Case Diagram

```mermaid
graph LR
    F2sys[F2]
    F4sys[F4]
    F7sys[F7]
    Beat[Celery Beat scheduler]
    Op[Operator]
    F2sys --> UC1((Find or create Project))
    F4sys --> UC2((Persist analysis row))
    F7sys --> UC3((Read analysis state))
    Beat --> UC4((Run cleanup jobs))
    Beat --> UC5((Run anonymization daily))
    Op --> UC6((Inspect system health))
    Op --> UC7((Manually trigger a job))
    Op --> UC8((Query privacy audit log))
```

**End of document.**
