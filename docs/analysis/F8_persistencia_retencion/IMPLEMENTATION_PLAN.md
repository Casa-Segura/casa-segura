# Implementation Plan — F8: Persistence, Project Entity & Retention

> Generated: 2026-05-15
> Stack: Django 5.2 LTS + Celery 5.4 + django-celery-beat + Postgres 15 + pgvector
> Module: `platform/` at the project root.

---

## Directory Structure

```
platform/
├── domain/
│   ├── entities.py           # Project, ContractAnalysis (central), PrivacyAuditLog, JobExecutionLog, AnonymizedEconomicSummary
│   ├── enums.py              # ContractType, Band, Severity, OverrideCode, PrivacyAuditEvent, JobStatus, DeliveryStatusEnum
│   └── exceptions.py
├── application/
│   ├── commands.py           # FindOrCreateProject, CreatePlaceholderProject, RecomputeProjectMetrics, AnonymizeAnalysis, WritePrivacyAuditLog, WriteJobExecutionLog, MarkLinkExpired
│   ├── queries.py            # GetSystemHealth, GetProjectByNormalizedName, GetAnalysesPendingAnonymization, ListProjectsDueRecompute
│   ├── handlers/
│   │   ├── project_handlers.py
│   │   ├── analysis_handlers.py
│   │   ├── audit_handlers.py
│   │   └── job_handlers.py
│   └── services/
│       ├── project_service.py
│       ├── retention_service.py
│       └── anonymization_bucketizer.py
└── infrastructure/
    ├── django/
    │   ├── apps.py
    │   ├── models.py         # ProjectModel, ContractAnalysisModel, PrivacyAuditLogModel, JobExecutionLogModel
    │   ├── repositories.py
    │   ├── serializers.py
    │   ├── views.py          # HealthView, TriggerJobView, AuditLogView
    │   ├── urls.py
    │   ├── management/
    │   │   └── commands/
    │   │       └── seed_initial.py    # placeholder project + default versions
    │   └── migrations/
    │       ├── 0001_initial.py        # the central schema + views + triggers
    │       └── 0002_seed.py           # data seed
    └── celery/
        ├── retention_tasks.py         # cleanup_transient, expire_links, anonymize_old_analyses, audit_log_cleanup, recompute_project_metrics
        ├── beat_schedule.py           # periodic task definitions
        └── job_runner.py              # JobRunner with Redis lock
```

---

## App Configuration

```python
# platform/infrastructure/django/apps.py
from django.apps import AppConfig

class PlatformConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "platform.infrastructure.django"
    label = "platform"
    verbose_name = "Casa Segura — Platform (schema + retention)"

    def ready(self) -> None:
        # Register beat schedules at startup
        try:
            from platform.infrastructure.celery.beat_schedule import ensure_periodic_tasks
            ensure_periodic_tasks()
        except Exception:
            pass  # tolerate transient DB unavailability at startup
```

`INSTALLED_APPS` includes:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "django_prometheus",
    "softdelete",  # for SoftDeleteObject used by Project (optional; placeholder for future business tables)
    "platform.infrastructure.django",
    "ingestion.infrastructure.django",
    "classification.infrastructure.django",
    "corpus.infrastructure.django",
    "rubric.infrastructure.django",
    "economics.infrastructure.django",
    "reports.infrastructure.django",
    "delivery.infrastructure.django",
]

MIGRATION_MODULES = {
    "platform": "platform.infrastructure.django.migrations",
    "ingestion": "ingestion.infrastructure.django.migrations",
    "classification": "classification.infrastructure.django.migrations",
    "corpus": "corpus.infrastructure.django.migrations",
    "rubric": "rubric.infrastructure.django.migrations",
    "economics": "economics.infrastructure.django.migrations",
    "reports": "reports.infrastructure.django.migrations",
    "delivery": "delivery.infrastructure.django.migrations",
}

CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_TIMEZONE = "America/El_Salvador"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
```

---

## Domain Entities (Pydantic)

(See `ENTITY_RELATIONSHIP_DIAGRAM.md` for `Project`, `ContractAnalysis`, `PrivacyAuditLog`, `JobExecutionLog`.)

Additional:

```python
class AnonymizedEconomicSummary(BaseModel):
    contract_type: ContractType
    currency: str
    price_cash_bucket: str | None = None
    down_payment_pct_bucket: str | None = None
    annual_rate_pct_bucket: str | None = None
    term_months_bucket: str | None = None
    overcost_label: Literal["none","small","medium","large"] | None = None
    benchmark_comparisons: list[dict] = []  # only metric + assessment
    anonymized: bool = True
    benchmark_version: str
```

## Commands and Queries

```python
# platform/application/commands.py
from uuid import UUID
from pydantic import BaseModel
from platform.domain.entities import PrivacyAuditLog, JobExecutionLog


class FindOrCreateProject(BaseModel):
    canonical_name: str
    normalized_name: str


class CreatePlaceholderProject(BaseModel):
    short_hash: str  # 8 chars of submission_hash


class RecomputeProjectMetrics(BaseModel):
    project_id: UUID


class AnonymizeAnalysis(BaseModel):
    analysis_id: UUID


class WritePrivacyAuditLog(BaseModel):
    entry: PrivacyAuditLog


class WriteJobExecutionLog(BaseModel):
    entry: JobExecutionLog
```

```python
# platform/application/queries.py
from shared.domain.entities.cqrs import BaseGetAttributes, BaseFilterAttributes, Query


class GetSystemHealth(BaseGetAttributes, Query): pass

class GetProjectByNormalizedName(BaseGetAttributes, Query):
    normalized_name: str

class GetAnalysesPendingAnonymization(BaseFilterAttributes, Query):
    cutoff: str  # ISO datetime
    limit: int = 200

class ListProjectsDueRecompute(BaseFilterAttributes, Query):
    pass
```

## New Dependencies

| Package | Version | Reason |
|---|---|---|
| (most already covered by F1-F7) | | |
| `django-celery-beat` | ≥ 2.6 | DB scheduler |
| `django-prometheus` | ≥ 2.3 | /metrics |
| `redis` lock recipe | (within `redis`) | Distributed lock for `anonymize_old_analyses` |

---

## Story: US-01 Initialize schema

### Files to Create
- `platform/infrastructure/django/models.py` (Project, ContractAnalysis, PrivacyAuditLog, JobExecutionLog)
- `platform/infrastructure/django/migrations/0001_initial.py`
- `platform/infrastructure/django/migrations/0002_seed.py`
- `platform/infrastructure/django/management/commands/seed_initial.py` (idempotent fallback if the migration is replayed)

### Reference Code (selected)

```python
# platform/infrastructure/django/models.py
import uuid
from django.contrib.postgres.fields import ArrayField
from django.db import models
from softdelete.models import SoftDeleteObject
from common.infrastructure.django.models import ModelWithTimeStamps  # provides created_at/updated_at; for tables that use them
from platform.domain.enums import ContractType, Band, DeliveryStatusEnum, OverrideCode


class ProjectModel(models.Model):
    """Real estate project; aggregation unit. Never deleted."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Internal identifier.")
    canonical_name = models.TextField(help_text="Project name as it appears in the contract.")
    normalized_name = models.TextField(unique=True, help_text="Slug used for matching across submissions.")
    first_seen = models.DateTimeField(auto_now_add=True, help_text="When the project was first created in the system.")
    last_analyzed = models.DateTimeField(help_text="When the latest associated analysis ran.")
    last_recomputed_at = models.DateTimeField(null=True, blank=True, help_text="Last time avg_score and score_distribution were refreshed.")
    total_analyses = models.IntegerField(default=0, help_text="Count of associated analyses.")
    avg_score = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, help_text="Moving average score across associated analyses.")
    score_distribution = models.JSONField(default=dict, help_text="Counts per band: green, yellow, red.")
    metadata = models.JSONField(default=dict, help_text="Extensible. metadata.placeholder=true for unknown projects.")

    class Meta:
        db_table = "project"
        indexes = [
            models.Index(fields=["normalized_name"], name="idx_project_normalized"),
            models.Index(fields=["last_analyzed"], name="idx_project_last_analyzed"),
        ]

    def __str__(self) -> str:
        return f"Project {self.normalized_name}"


class ContractAnalysisModel(models.Model):
    """Central business entity. Anonymized at 90 days."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Internal identifier.")
    public_short_id = models.TextField(unique=True, help_text="Short id visible to the user (CS-YYYY-XXXXXX).")
    project = models.ForeignKey(ProjectModel, on_delete=models.PROTECT, related_name="analyses", help_text="Owning project.")
    submission_hash = models.TextField(db_index=True, help_text="SHA-256 of submission for deduplication.")

    # Classification
    contract_type = models.CharField(max_length=16, help_text="Detected contract type (after possible reclassification).")
    contract_type_declared = models.CharField(max_length=16, null=True, blank=True, help_text="What the document presents itself as.")
    contract_type_reclassified = models.BooleanField(default=False, help_text="True if reclassified.")
    reclassification_reason = models.TextField(null=True, blank=True, help_text="Justification when reclassified.")
    reclassification_indicators = models.JSONField(null=True, blank=True, help_text="Structured Art. 2 LAF indicator detection.")
    classification_confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True, help_text="LLM confidence 0..1.")
    classification_attempts = models.IntegerField(default=1, help_text="1 or 2 attempts.")
    elements_detected = models.JSONField(null=True, blank=True, help_text="Boolean flag map of legal elements detected.")

    # Analysis result
    score_total = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True, help_text="Total score 0..10; forced to 0 by overrides.")
    band = models.CharField(max_length=16, null=True, blank=True, help_text="green/yellow/red/not_analyzable.")
    override_triggered = ArrayField(models.CharField(max_length=64), default=list, blank=True, help_text="List of triggered override codes.")
    scores_by_category = models.JSONField(null=True, blank=True, help_text="Per-category scores.")
    criterion_evaluations = models.JSONField(null=True, blank=True, help_text="Per-criterion evaluations; erased at anonymization.")
    findings = models.JSONField(null=True, blank=True, help_text="Findings with legal_basis and recommendations; erased at anonymization.")
    findings_count = models.IntegerField(default=0, help_text="Total findings.")
    critical_findings_count = models.IntegerField(default=0, help_text="Critical-severity findings count.")
    unverifiable_count = models.IntegerField(default=0, help_text="Unverifiable criteria count.")
    executive_summary = models.TextField(null=True, blank=True, help_text="2-3 sentence summary; preserved at anonymization.")
    economic_summary = models.JSONField(null=True, blank=True, help_text="Economic summary; bucketed at anonymization.")

    # Versioning
    rubric_version = models.CharField(max_length=32, null=True, blank=True, help_text="Rubric version used.")
    corpus_version = models.CharField(max_length=32, null=True, blank=True, help_text="Corpus version used.")
    benchmark_version = models.CharField(max_length=32, null=True, blank=True, help_text="Benchmark version used.")

    # Delivery state
    delivery_status = models.CharField(max_length=16, default="pending", help_text="Current delivery state.")
    delivery_channel = models.CharField(max_length=24, null=True, blank=True, help_text="Channel chosen by user.")
    delivery_target_hash = models.TextField(null=True, blank=True, help_text="salt+SHA-256 of destination; erased at anonymization.")
    link_expires_at = models.DateTimeField(null=True, blank=True, help_text="Public link expiration.")
    resend_count = models.IntegerField(default=0, help_text="Resends issued (max 3).")

    # Anonymization
    anonymized_at = models.DateTimeField(null=True, blank=True, help_text="When the row was anonymized.")

    created_at = models.DateTimeField(auto_now_add=True, help_text="Created timestamp.")

    class Meta:
        db_table = "contract_analysis"
        indexes = [
            models.Index(fields=["project"], name="idx_analysis_project"),
            models.Index(fields=["public_short_id"], name="idx_analysis_short_id"),
            models.Index(fields=["submission_hash"], name="idx_analysis_subhash"),
            models.Index(fields=["link_expires_at"], name="idx_analysis_link_exp", condition=models.Q(link_expires_at__isnull=False)),
            models.Index(fields=["anonymized_at"], name="idx_analysis_anon", condition=models.Q(anonymized_at__isnull=True)),
            models.Index(fields=["created_at"], name="idx_analysis_created"),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(score_total__gte=0) & models.Q(score_total__lte=10), name="ca_score_range"),
        ]

    def __str__(self) -> str:
        return f"ContractAnalysis {self.public_short_id}"


class PrivacyAuditLogModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    event_type = models.CharField(max_length=64, help_text="Audit event type.")
    related_id = models.UUIDField(null=True, blank=True, help_text="Affected row id.")
    related_table = models.CharField(max_length=128, null=True, blank=True, help_text="Affected table name.")
    event_data = models.JSONField(null=True, blank=True, help_text="Extensible payload.")
    triggered_by = models.CharField(max_length=128, null=True, blank=True, help_text="Operator or system.")
    occurred_at = models.DateTimeField(auto_now_add=True, help_text="Event time.")
    expires_at = models.DateTimeField(help_text="Cleanup time (default +1 year).")

    class Meta:
        db_table = "privacy_audit_log"
        indexes = [
            models.Index(fields=["event_type"], name="idx_audit_event"),
            models.Index(fields=["occurred_at"], name="idx_audit_occurred"),
            models.Index(fields=["expires_at"], name="idx_audit_expires"),
        ]


class JobExecutionLogModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    job_name = models.CharField(max_length=128, db_index=True, help_text="Periodic job name.")
    started_at = models.DateTimeField(auto_now_add=True, help_text="Run start.")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="Run end.")
    status = models.CharField(max_length=16, help_text="running/success/failed.")
    records_processed = models.IntegerField(null=True, blank=True, help_text="Rows touched.")
    error_message = models.TextField(null=True, blank=True, help_text="If failed.")
    expires_at = models.DateTimeField(help_text="Cleanup time (default +30 days).")

    class Meta:
        db_table = "job_execution_log"
        indexes = [
            models.Index(fields=["started_at"], name="idx_jobs_started"),
            models.Index(fields=["expires_at"], name="idx_jobs_expires"),
        ]
```

### Migration 0001_initial — sketch

```python
class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS pgcrypto;", reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";", reverse_sql=migrations.RunSQL.noop),
        migrations.RunSQL("CREATE EXTENSION IF NOT EXISTS vector;", reverse_sql=migrations.RunSQL.noop),
        # CreateModel for the four F8 tables
        # ...
        # Views and triggers via RunSQL:
        migrations.RunSQL(
            "CREATE VIEW v_system_health AS SELECT ... ;",
            reverse_sql="DROP VIEW IF EXISTS v_system_health;",
        ),
        migrations.RunSQL(
            "CREATE VIEW v_retention_status AS SELECT ... ;",
            reverse_sql="DROP VIEW IF EXISTS v_retention_status;",
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION reject_catalog_mutation() RETURNS trigger AS $$
            BEGIN
                IF (row_to_json(OLD)::jsonb - 'is_active') IS DISTINCT FROM (row_to_json(NEW)::jsonb - 'is_active') THEN
                    RAISE EXCEPTION 'Versioned catalog row is immutable except for is_active';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """,
            reverse_sql="DROP FUNCTION IF EXISTS reject_catalog_mutation();",
        ),
        # (triggers per catalog table are added in the respective module's migration once the table exists.)
    ]
```

### Migration 0002_seed

```python
def seed(apps, schema_editor):
    ProjectModel = apps.get_model("platform", "ProjectModel")
    if not ProjectModel.objects.filter(normalized_name="__unknown_pending__").exists():
        ProjectModel.objects.create(
            canonical_name="Pending project assignment",
            normalized_name="__unknown_pending__",
            last_analyzed=timezone.now(),
            metadata={"placeholder": True, "system": True},
        )

class Migration(migrations.Migration):
    dependencies = [("platform", "0001_initial")]
    operations = [migrations.RunPython(seed, reverse_code=migrations.RunPython.noop)]
```

---

## Story: US-02 Project find_or_create

`ProjectRepository.upsert` uses raw SQL because Django ORM doesn't have a clean ON CONFLICT for the returning xmax pattern. Reference:

```python
def upsert(self, canonical_name: str, normalized_name: str) -> tuple[Project, bool]:
    with connection.cursor() as cur:
        cur.execute(
            """
            INSERT INTO project (id, canonical_name, normalized_name, first_seen, last_analyzed, total_analyses, score_distribution, metadata)
            VALUES (gen_random_uuid(), %s, %s, NOW(), NOW(), 0, '{"green":0,"yellow":0,"red":0}'::jsonb, '{}'::jsonb)
            ON CONFLICT (normalized_name)
            DO UPDATE SET last_analyzed = NOW(), canonical_name = EXCLUDED.canonical_name
            RETURNING id, (xmax = 0) AS was_inserted
            """,
            [canonical_name, normalized_name],
        )
        row = cur.fetchone()
    project_id, was_inserted = row
    return self.get_by_id(project_id), bool(was_inserted)
```

## Story: US-03..US-09 Periodic jobs

Listed in Stage 8 below. Each task wraps its work in `JobRunner.run(name, fn)` which:
- Acquires a Redis lock when applicable.
- Writes `JobExecutionLog(status=running)` at start, updates at end.

```python
# platform/infrastructure/celery/job_runner.py
import redis
from datetime import datetime
from contextlib import contextmanager

class JobRunner:
    def __init__(self, *, redis_client, log_repo):
        self.redis_client = redis_client
        self.log_repo = log_repo

    @contextmanager
    def run(self, job_name: str, *, with_lock: bool = False, lock_timeout: int = 1800):
        lock = None
        if with_lock:
            lock = self.redis_client.lock(f"job:{job_name}", timeout=lock_timeout, blocking=False)
            if not lock.acquire(blocking=False):
                yield "lock_held"
                return
        entry = self.log_repo.create_running(job_name)
        try:
            yield entry
            self.log_repo.mark_success(entry.id)
        except Exception as e:
            self.log_repo.mark_failed(entry.id, str(e))
            raise
        finally:
            if lock:
                try:
                    lock.release()
                except Exception:
                    pass
```

## Story: US-10 Versioned catalog immutability

The trigger function `reject_catalog_mutation` is created in F8's 0001_initial; per-table triggers attach in each owning module's migration (after the table exists).

---

## Part 2 — Staged Execution Plan

### Codebase Alignment Rules

- Django 5.2 LTS
- `platform` app owns: schema for the central business + observability tables; all retention jobs.
- Other modules own their own catalog/transient tables and add per-table triggers in their own migrations.
- All Celery tasks `@shared_task(name="platform.<name>")`.
- All env vars under `PLATFORM_*`.
- Beat scheduler: `django_celery_beat.schedulers.DatabaseScheduler`.

### Stage Overview

| # | Stage | Deliverable |
|---|---|---|
| 1 | Domain entities/enums/exceptions | Pydantic + TextChoices |
| 2 | Commands/queries | CQRS |
| 3 | Handlers | Plain functions |
| 4 | Service classes | ProjectService, RetentionService, AnonymizationBucketizer, JobRunner |
| 5 | Django models + initial migration + views + trigger function | platform.0001_initial.py |
| 6 | Seed migration | platform.0002_seed.py |
| 7 | Repositories | ProjectRepository, ContractAnalysisRepository (central), PrivacyAuditLogRepository, JobExecutionLogRepository |
| 8 | Celery tasks + Beat schedule | retention_tasks.py + beat_schedule.py |
| 9 | DRF views + URLs | HealthView, TriggerJobView, AuditLogView |
| 10 | Tests | unit + integration; golden bucket tests; idempotency tests |
| 11 | Observability | Prometheus metrics + alerts |
| 12 | Documentation | RUNBOOK + backups + restore drill notes |

### Stage 8 — Celery tasks + Beat schedule

```python
# platform/infrastructure/celery/retention_tasks.py
from celery import shared_task

@shared_task(name="platform.cleanup_transient")
def cleanup_transient():
    from platform.application.services.retention_service import RetentionService
    return RetentionService(...).cleanup_transient()

@shared_task(name="platform.cleanup_delivery_targets")
def cleanup_delivery_targets():
    from delivery.infrastructure.celery.delivery_tasks import cleanup_delivery_targets as inner
    return inner()  # F7 owns the impl

@shared_task(name="platform.expire_links")
def expire_links():
    from delivery.infrastructure.celery.delivery_tasks import expire_links as inner
    return inner()

@shared_task(name="platform.anonymize_old_analyses")
def anonymize_old_analyses(batch_size: int = 200):
    from platform.application.services.retention_service import RetentionService
    return RetentionService(...).anonymize_old_analyses(batch_size=batch_size)

@shared_task(name="platform.recompute_project_metrics")
def recompute_project_metrics():
    from platform.application.services.project_service import ProjectService
    return ProjectService(...).recompute_all_due()

@shared_task(name="platform.audit_log_cleanup")
def audit_log_cleanup():
    from platform.application.services.retention_service import RetentionService
    return RetentionService(...).audit_log_cleanup()
```

```python
# platform/infrastructure/celery/beat_schedule.py
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule

def ensure_periodic_tasks():
    every_5m, _ = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.MINUTES)
    every_15m, _ = IntervalSchedule.objects.get_or_create(every=15, period=IntervalSchedule.MINUTES)
    every_1h, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.HOURS)
    every_1m, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.MINUTES)
    crontab_03, _ = CrontabSchedule.objects.get_or_create(minute="0", hour="3", day_of_week="*", day_of_month="*", month_of_year="*", timezone="America/El_Salvador")
    crontab_sun_04, _ = CrontabSchedule.objects.get_or_create(minute="0", hour="4", day_of_week="0", day_of_month="*", month_of_year="*", timezone="America/El_Salvador")

    PeriodicTask.objects.update_or_create(name="platform.cleanup_transient", defaults={"task": "platform.cleanup_transient", "interval": every_15m})
    PeriodicTask.objects.update_or_create(name="platform.cleanup_delivery_targets", defaults={"task": "platform.cleanup_delivery_targets", "interval": every_5m})
    PeriodicTask.objects.update_or_create(name="platform.expire_links", defaults={"task": "platform.expire_links", "interval": every_1h})
    PeriodicTask.objects.update_or_create(name="platform.anonymize_old_analyses", defaults={"task": "platform.anonymize_old_analyses", "crontab": crontab_03})
    PeriodicTask.objects.update_or_create(name="platform.recompute_project_metrics", defaults={"task": "platform.recompute_project_metrics", "interval": every_1h})
    PeriodicTask.objects.update_or_create(name="platform.audit_log_cleanup", defaults={"task": "platform.audit_log_cleanup", "crontab": crontab_sun_04})
    PeriodicTask.objects.update_or_create(name="delivery.retry_due_deliveries", defaults={"task": "delivery.retry_due_deliveries", "interval": every_1m})
```

### Stage 11 — Metrics & alerts

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `f8_job_latency_seconds` | Histogram | `job_name` | Per-job latency |
| `f8_job_outcome_total` | Counter | `job_name`, `outcome` | Funnel |
| `f8_records_processed_total` | Counter | `job_name` | Throughput |
| `f8_anonymization_pending` | Gauge | — | From `v_retention_status` |
| `f8_pending_anonymization_age_seconds` | Histogram | — | Oldest pending anonymization age |
| `f8_table_row_count` | Gauge | `table_name` | Size of each table |
| `f8_audit_log_writes_total` | Counter | `event_type` | Audit volume |

Alerts:

```yaml
- alert: F8AnonymizationOverdue
  expr: f8_anonymization_pending > 100
  for: 6h
- alert: F8JobNotRun
  # job's last successful run older than 2× its interval
- alert: F8RetentionStatusOverdue
  expr: v_retention_status overdue rows for contract_submission > 1000
```

---

## Error Codes

| Code | Description |
|---|---|
| `JOB_LOCK_HELD` | Job skipped because another instance holds the lock |
| `MIGRATION_MISMATCH` | Application started on an environment whose schema is older than code |
| `EXTENSION_MISSING` | Postgres extension not installed |

---

## Configuration matrix

| Variable | Default | Purpose |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | — | DB connection |
| `DB_POOL_MIN_SIZE` | 5 | — |
| `DB_POOL_MAX_SIZE` | 20 | — |
| `ANONYMIZATION_AFTER_DAYS` | 90 | Anonymization horizon |
| `JOB_BATCH_SIZE` | 200 | Anonymization batch |
| `JOB_TIMEZONE` | `America/El_Salvador` | Beat tz |
| `REDIS_URL` | — | Lock backend |
| `RETENTION_TRANSIENT_INTERVAL_MIN` | 15 | — |
| `RETENTION_DELIVERY_TARGET_INTERVAL_MIN` | 5 | — |
| `RETENTION_EXPIRE_LINKS_INTERVAL_MIN` | 60 | — |
| `RETENTION_RECOMPUTE_PROJECT_INTERVAL_MIN` | 60 | — |
| `RETENTION_ANONYMIZE_CRON` | `0 3 * * *` | — |
| `RETENTION_AUDIT_CLEANUP_CRON` | `0 4 * * 0` | — |

---

**End of document.**
