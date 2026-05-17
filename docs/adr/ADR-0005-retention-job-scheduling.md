# ADR-0005: Retention job scheduling (Celery Beat + single leader)

- **Status:** Accepted  
- **Date:** 2026-05-16  
- **Context:** PRD **F8** ([`PRD_F8_PERSISTENCIA_PROYECTO_RETENCION`](../../Casa%20Segura%20Formal%20PRDs/PRD_F8_PERSISTENCIA_PROYECTO_RETENCION.md) §6.2, §6.3, BR-13) requires five recurring housekeeping jobs plus observable runs. Backend stack already mandates **Celery** + **Redis** + **`django-celery-beat`** ([ADR-0001](ADR-0001-django-backend-stack.md)).

## Decision

1. **Primary scheduler:** **`django-celery-beat`** driving **Celery periodic tasks**. One deployment **runs exactly one `celery beat` process** (see `RAILWAY.md` worker/beat topology). Periodic tasks enqueue work that workers execute (**at-least-once**); every job implementation **must remain idempotent** (safe under duplicate enqueue or retry).
2. **Rejected — APScheduler embedded in HTTP workers:** Risks duplicated ticks when horizontally scaling API/gunicorn processes; duplicates conflict with hourly/daily budgets unless we introduce ad-hoc leader election.
3. **Rejected — raw OS cron alone as MVP standard:** Leaves schedule definitions split from code review and complicates parity between local Docker and hosted worker images; cron may supplement **manual or emergency** invokes only.
4. **Duplicate-scheduler mitigation:** Production **requires** a single **beat** service instance. Scaling **workers** horizontally is encouraged; scaling **beat** beyond one instance is forbidden unless coordinated with infra (leader election explicitly designed and documented). Operational duplicate detection: alert if identical job emits success more than twice per expected window (see §BVA tie-in to BR-13).
5. **Manual / ops invokes:** Each job exposes a **`manage.py run_retention_job <job_name>`** shim thin-wrapping the same callable Celery invokes (implementations delivered in CS-271..CS-275). Exit codes: `0` success, `1` logical failure/partial retry, `2` misconfiguration.
6. **Internal HTTP triggers:** PRD F8 §7.2 `POST /v1/internal/jobs/trigger/{job_name}` stays **optional** for MVP — documented here as **defer** until infra auth story exists ([CS-270](../Roadmap/tickets/CS-270.md) scope Out).

### Schedule table vs PRD F8 §6.2

Configured **maximum** cadence anchors (implementations tighten but must remain within SLA):

| Job | PRD SLA | Periodic contract (initial) |
| --- | --- | --- |
| `cleanup_transient` | ≤ **15 min** | `crontab` / interval every **≤15 minutes** (`900` s nominal) |
| `cleanup_delivery_targets` | ≤ **5 min** | interval every **≤5 minutes** (`300` s nominal) |
| `expire_links` | ≤ **1 h** | interval every **≤60 minutes** (`3600` s nominal) |
| `anonymize_old_analyses` | Daily **03:00 America/El_Salvador** | `crontab` **hour = 3, minute = 0**, `timezone = America/El_Salvador` |
| `recompute_project_metrics` | ≤ **1 h** | interval every **≤60 minutes** (`3600` s nominal) |

**DST note:** Today **America/El_Salvador** has **no daylight saving transitions** (`zoneinfo` reflects civil authority). If policy changes later, rerun BVA tied to DST boundary days.

### Job entrypoints (callable contract)

Tasks + CLI map to snake_case identifiers below. Business logic stubs land in subsequent tickets (**CS-271 … CS-275**).

| `job_name` | Celery task path (planned) | Manual CLI |
| --- | --- | --- |
| `cleanup_transient` | `platform_core.worker.retention.tasks.cleanup_transient` | `manage.py run_retention_job cleanup_transient` |
| `cleanup_delivery_targets` | `platform_core.worker.retention.tasks.cleanup_delivery_targets` | same pattern |
| `expire_links` | `platform_core.worker.retention.tasks.expire_links` | same pattern |
| `anonymize_old_analyses` | `platform_core.worker.retention.tasks.anonymize_old_analyses` | same pattern |
| `recompute_project_metrics` | `platform_core.worker.retention.tasks.recompute_project_metrics` | same pattern |

### Structured metrics (BR-13)

Each run emits **one structured log JSON object per attempt** (`structlog` per CS-007) with mandatory keys:

- `job_name` (string)  
- `started_at`, `completed_at` (ISO-8601 UTC recommended)  
- `status`: `started` | `success` | `failed` | `partial`  
- `records_processed` (int, `-1` if unknown pre-scan)  

Optional additive keys: `error_code`, `error_message` (bounded length, scrub PII).

## Consequences

- **Positive:** Aligns infra with existing Django/Celery lock-in; reviewers see schedules in-repo via beat DB migrations + task modules.  
- **Positive:** At-least-once + idempotency simplifies retries after deploy or Redis blips.  
- **Operational:** Teams must allocate **exactly-one beat** replicas in prod-like environments; playbook should call this out beside worker autoscaling knobs.

## Validation harness

Dry validation (parses TZ, asserts cadence literals against this table — **no database**):

```bash
cd backend && poetry run python scripts/retention_scheduler_dry_validate.py
# or:
make retention-scheduler-dry-validate
```

## Related

- [ADR-0001](ADR-0001-django-backend-stack.md), `RAILWAY.md`, `.github/workflows/ci.yml` (`backend-lint` step)  
- Tickets **CS-270** … **CS-276**, **PRD_F8**, **FEATURES_MAP** Phase 6
