# Complete Flows — F8: Persistence, Project Entity & Retention

> Generated: 2026-05-15

---

## Flow Index

| # | Flow |
|---|---|
| 1 | Schema initialization (migrate) |
| 2 | Find or create Project (called by F2) |
| 3 | Recompute project metrics (hourly) |
| 4 | cleanup_transient (every 15 min) |
| 5 | cleanup_delivery_targets (every 5 min) |
| 6 | expire_links (hourly) |
| 7 | anonymize_old_analyses (daily 03:00) |
| 8 | audit_log_cleanup (weekly) |
| 9 | System health (operator) |
| 10 | Manual job trigger (operator) |
| 11 | Manual data deletion (ARCO-right v1.1, recommended) |

---

## Flow 1: Schema initialization

### Pre-conditions
- New environment; Postgres 15 with `pgvector` available.

### Happy Path

1. Operator runs `python manage.py migrate`.
2. Django applies migrations in dependency order:
   - `platform.0001_initial.py`: extensions + `project`, `contract_analysis`, `privacy_audit_log`, `job_execution_log`, both views (`v_system_health`, `v_retention_status`).
   - `platform.0002_seed.py`: placeholder project, `rubric_version.1.0.0`, `corpus_version.YYYY-MM-DD`, `benchmark_version.YYYY-QN` (rows only — actual chunks/criteria/benchmarks loaded separately by F3/F4/F5 commands).
   - `rubric.0001_initial.py`, `rubric.0002_seed_v1_0_0.py`: rubric tables + 38 criteria.
   - `corpus.0001_initial.py`: corpus tables + HNSW index.
   - `economics.0001_initial.py` + `0002_seed`: benchmarks.
   - `ingestion.0001_initial.py`: no-op (re-imports).
   - `classification.0001_initial.py`: classification_job table.
   - `reports.0001_initial.py`: report_generation_log table.
   - `delivery.0001_initial.py` + `0002_audit_view.py`: delivery_request + view.
3. `python manage.py check --deploy` passes.
4. `python manage.py corpus_ingest --version YYYY-MM-DD --path corpus/laws/` ingests the actual corpus.

---

## Flow 2: Find or create Project

### Trigger
F2 calls `project_service.find_or_create("Residencial Las Palmeras","las palmeras")`.

### Happy Path

1. `ProjectRepository.upsert(canonical, normalized)`.
2. Postgres `INSERT ... ON CONFLICT (normalized_name) DO UPDATE SET last_analyzed=NOW(), canonical_name=EXCLUDED.canonical_name RETURNING id, (xmax = 0) AS was_inserted`.
3. Returns `(project_id, was_inserted)`. F2 uses the id; the boolean is for metrics.

### Notes

- `total_analyses` is **not** incremented inline (avoids contention). The hourly recompute cron handles it.
- Placeholder projects (`metadata.placeholder=true`) bypass the upsert; F2 calls a separate `ProjectRepository.create_placeholder(short_hash)` which always INSERTs.

---

## Flow 3: Recompute project metrics

### Trigger
Hourly Celery Beat task `recompute_project_metrics`.

### Happy Path

1. Find projects with `last_recomputed_at IS NULL OR last_recomputed_at < last_analyzed`, excluding placeholders.
2. For each: `UPDATE project SET avg_score = (...), score_distribution = (...), total_analyses = (...), last_recomputed_at = NOW() WHERE id = $1`.
3. Returns `{recomputed: N}`.

### Notes

- Anonymized analyses still count (they preserve `score_total`).
- Failed analyses with `band='not_analyzable'` are included or excluded per product decision; current default: **excluded** from `avg_score`, **included** in `total_analyses`.

---

## Flow 4: cleanup_transient

### Trigger
Celery Beat every 15 minutes.

### Happy Path

1. `DELETE FROM contract_submission WHERE expires_at < NOW() AND processing_status NOT IN ('received','extracting','classifying','analyzing') LIMIT 10000`.
2. `ON DELETE CASCADE` on `ocr_job` removes children.
3. If `N >= 10000`, the task self-reschedules immediately (the next 15-min window won't suffice).
4. Audit log entry: `event_type='submission_purged'`, `event_data={count:N}`.

### Notes

- The `NOT IN (...)` guard avoids deleting submissions still being processed; the F1 stuck-submissions task marks those `expired` first.

---

## Flow 5: cleanup_delivery_targets

(See F7 Flow 8 — same task; implementation in `delivery/celery/`. F8 owns the schedule.)

---

## Flow 6: expire_links

(See F7 Flow 7 — same task; implementation in `delivery/celery/`. F8 owns the schedule.)

---

## Flow 7: anonymize_old_analyses

### Trigger
Daily at 03:00 `America/El_Salvador` via Celery Beat.

### Happy Path

1. Acquire Redis lock `job:anonymize_old_analyses` (timeout 30 min, non-blocking). If held → exit `lock_held`.
2. Loop in batches of 200:
   - `SELECT id, economic_summary FROM contract_analysis WHERE anonymized_at IS NULL AND created_at < NOW() - INTERVAL '90 days' ORDER BY created_at LIMIT 200`.
   - For each row:
     - `bucketed = AnonymizationBucketizer.bucketize(economic_summary)`.
     - `BEGIN`; `UPDATE contract_analysis SET delivery_target_hash=NULL, criterion_evaluations=NULL, findings=NULL, economic_summary=$bucketed, anonymized_at=NOW() WHERE id=$1`; `INSERT INTO privacy_audit_log (...)`; `COMMIT`.
3. If batch returned 200 rows, loop again.
4. Release lock.
5. Return `{anonymized: total}`.

### Failure handling

- On exception: log to `job_execution_log` with `status=failed`, release lock, re-raise. Beat will retry the next day (or operator triggers manually).
- The job has a `pause` mechanism: if 10+ consecutive UPDATE failures occur, the task aborts the loop and emits an ops alert (auto-pause to prevent corruption cascade).

### Post-conditions

- Rows with `anonymized_at IS NOT NULL` exist; their snippets and exact economic values are erased.
- Project metrics are re-computed next hour.

---

## Flow 8: audit_log_cleanup

### Trigger
Weekly (Sunday 04:00 local).

### Happy Path

```sql
DELETE FROM privacy_audit_log WHERE expires_at < NOW() LIMIT 100000;
DELETE FROM job_execution_log WHERE expires_at < NOW();
DELETE FROM rag_query_log WHERE expires_at < NOW();
DELETE FROM classification_job WHERE expires_at < NOW();
DELETE FROM report_generation_log WHERE expires_at < NOW();
```

Each command separately; counts logged.

---

## Flow 9: System health (operator)

### Trigger
`GET /v1/internal/health/db` with `X-Internal-Auth`.

### Happy Path

1. View executes `SELECT * FROM v_system_health`.
2. Returns the row as JSON.
3. Operator uses Grafana/Prometheus to chart over time; this endpoint is for ad-hoc checks.

---

## Flow 10: Manual job trigger

### Trigger
`POST /v1/internal/jobs/trigger/{job_name}` with `X-Internal-Auth`.

### Happy Path

1. View whitelist-checks `job_name` against the set of registered jobs.
2. Looks up the task by name in Celery registry.
3. Calls `task.delay()` with optional kwargs from request body.
4. Returns `{task_id, queued_at}`.

### Notes

- Use case: a 03:00 anonymization failed; ops triggers it manually before next scheduled run.

---

## Flow 11: Manual data deletion (ARCO right, v1.1 recommended)

### Trigger
`POST /v1/contracts/{short_id}/destroy` with `{target: "..."}`; auth = hash match.

### Happy Path

1. Verify hash match (same as resend Flow 5 in F7).
2. Mark analysis `delivery_status='destroyed'` (new enum value if implemented).
3. Force anonymization immediately on this row (bypassing the 90-day rule).
4. Audit log entry `event_type='manual_data_deletion'`.
5. The `submission_hash` is preserved (per privacy assumption — not PII).

### Status

**Recommended for v1.1**. Documented here for traceability.

---

**End of document.**
