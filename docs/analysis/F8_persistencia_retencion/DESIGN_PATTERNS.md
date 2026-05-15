# Design Patterns — F8: Persistence, Project Entity & Retention

> Generated: 2026-05-15

---

## Patterns Applied

### Cron / Periodic Task

**Why it fits:** Retention obligations are time-based ("after 24 h", "after 90 days"). Continuous polling for these would waste resources; periodic tasks run on schedule and idempotently move state forward.

**Implementation:** `django-celery-beat` with `DatabaseScheduler`. Schedules declared in code via `PeriodicTask` + `IntervalSchedule`/`CrontabSchedule` ORM rows seeded in a data migration. Tasks themselves are `@shared_task`.

---

### Idempotent Jobs

**Why it fits:** Two simultaneous runs of `anonymize_old_analyses` must not double-anonymize. A run that crashes mid-batch must be safe to restart from where it stopped.

**Implementation:** All anonymization queries filter by `anonymized_at IS NULL`; once a row is anonymized, subsequent runs see it as done. Transient cleanup uses `DELETE … WHERE expires_at < NOW()` — idempotent. Project recompute uses `last_recomputed_at < last_analyzed` — idempotent.

---

### Batch Processing with Pagination

**Why it fits:** The anonymization batch could be 1,000–5,000 rows daily. Processing them in one transaction holds locks too long; processing one at a time is too chatty. Batches of 200 with separate transactions balance the two.

**Implementation:** `RetentionService.anonymize_old_analyses(batch_size=200)`. If the result indicates `has_more=true`, the task self-chains: `anonymize_old_analyses.apply_async(args=[200], countdown=60)`.

---

### Single-Writer Catalog (Versioned Immutable Catalog)

**Why it fits:** `RubricVersion`, `CorpusVersion`, `BenchmarkVersion` must not silently mutate. Multiple operators could attempt updates. The `BEFORE UPDATE` trigger ensures only the `is_active` flag changes.

**Implementation:** PostgreSQL trigger function `reject_catalog_mutation()` plus three triggers, one per versioned catalog.

---

### Anti-corruption Layer (Anonymization Bucketizer)

**Why it fits:** The bucket boundaries are policy decisions, not algorithm. Encapsulating them in `AnonymizationBucketizer` keeps anonymization deterministic and the policy easy to inspect.

**Implementation:** A class with one method per bucket type. Tested with golden examples.

---

### Observer / Audit Trail

**Why it fits:** Every privacy-sensitive action must be auditable. `PrivacyAuditLog` is the trail. Writing it is a direct INSERT inside the same transaction as the privacy action (so a rollback rolls back the audit entry as well).

**Implementation:** `RetentionService` writes audit entries inline. F3 (corpus publication), F2 (placeholder project creation when meaningful), and F7 (delivery target purge) also write.

---

### Distributed Lock for Long Jobs

**Why it fits:** If two `anonymize_old_analyses` tasks run simultaneously (Beat misconfigured, two workers), one would see rows the other already updated and write duplicate audit logs. A Redis SETNX lock with TTL ensures at most one runs.

**Implementation:** `JobRunner.run("anonymize_old_analyses", fn)` wraps the call in `with redis.lock("job:anonymize_old_analyses", timeout=1800, blocking=False):`. If lock cannot be acquired, the task exits with `lock_held` status.

---

### Bulkhead (per-job DB connection budget)

**Why it fits:** A misbehaving heavy job (anonymization batch) shouldn't starve the API. Different Celery queues/workers separate concerns.

**Implementation:** Beat dispatches to a dedicated `retention` Celery queue; workers for that queue have a separate DB connection pool from the API.

---

## Patterns Considered and Rejected

### Database trigger-driven cascading anonymization

Tempting: have Postgres triggers anonymize rows automatically. Rejected because: bucket calculations are non-trivial; triggers obscure logic; debugging anonymization bugs in pure SQL is painful.

### Soft-delete on transient tables

Tempting: mark them deleted instead of hard-deleting. Rejected because: defeats the purpose (we want them gone); the PRD demands actual deletion; storage cost is real.

### Event sourcing for the audit log

Tempting: log every state change. Rejected because: only privacy-sensitive events matter for the regulator-facing audit. General state-change logging is operational and lives in `structlog` outputs.

### Per-project sharding

If the system grows to millions of projects, the project table could shard. Rejected at MVP; the table is the smallest one in the system.

### Logical replication for backup

Tempting for HA. Out of MVP scope; documented for v2.

---

**End of document.**
