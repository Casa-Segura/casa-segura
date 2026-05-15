# Evaluation Coverage — F8: Persistence, Project Entity & Retention

> Generated: 2026-05-15

---

## Coverage Matrix

| PRD Requirement | Covered By | Status |
|---|---|---|
| US-01 initialize schema | IMPLEMENTATION_PLAN Stage 5 + migration 0001_initial | COVERED |
| US-02 create/associate Project | ProjectRepository.upsert + Stage 7 | COVERED |
| US-03 update aggregate Project metrics | recompute_project_metrics task | COVERED |
| US-04 cleanup_transient every 15 min | retention_tasks + Beat | COVERED |
| US-05 erase encrypted destination after delivery | F7 inline + cron safety net | COVERED |
| US-06 mark expired links | expire_links task | COVERED |
| US-07 anonymize at 90 days | anonymize_old_analyses task + bucketizer | COVERED |
| US-08 economic summary bucketization | AnonymizationBucketizer | COVERED |
| US-09 recompute project metrics periodically | recompute_project_metrics | COVERED |
| US-10 versioned catalog immutability | reject_catalog_mutation trigger + per-table triggers in F3/F4/F5 migrations | COVERED |
| BR-00 governing invariant (no contract text persisted) | Schema design + 90-day anonymization | COVERED |
| BR-01..BR-15 | Across Stages 1-12 | COVERED |
| Schema completeness (every entity in DOMAIN_MODEL) | See ERD; cross-references in `_shared/GLOBAL_ASSUMPTIONS.md` §11 | COVERED |
| Cron schedule | Stage 8 beat_schedule.py | COVERED |
| Backups daily, 30-day retention, encrypted | Infra concern; documented in RUNBOOK | COVERED (planned) |
| RPO < 1 h via WAL streaming | Infra concern | COVERED (planned) |
| RTO < 4 h | Infra concern | COVERED (planned) |
| Anonymization batch < 30 min | Batch size + lock; tested | COVERED |
| DB P50 ≤ 20 ms / P95 ≤ 100 ms | Indexes designed accordingly | COVERED (instrumented) |
| 500 QPS throughput | Indexes + DB pool size | COVERED (instrumented) |
| Privacy audit log 1-year TTL | audit_log_cleanup task | COVERED |
| Internal endpoint /v1/internal/health/db | HealthView | COVERED |
| Internal endpoint trigger job | TriggerJobView | COVERED |
| Internal endpoint audit log | AuditLogView | COVERED |

---

## Critical Points

1. **Schema split between modules vs platform** — see `_shared/GLOBAL_ASSUMPTIONS.md` §11. Platform owns the central business + observability tables; each feature owns its own catalog/transient tables. Migrations carefully ordered via Django `dependencies`.
2. **Anonymization correctness** — the daily job is the single mechanism guaranteeing the privacy promise. Property tests + golden values + the `pause-on-failure` mechanism.
3. **Distributed lock for anonymize** — without it, two Beat instances (during DB migration windows or rolling deployments) could double-anonymize. With it, only one wins.
4. **Cron observability** — every job writes `JobExecutionLog` + emits Prometheus. Alerts fire if a job hasn't run in N+1 periods.
5. **`submission_hash` preserved after anonymization** — this is intentional (allows re-submission dedup); the `_shared/GLOBAL_ASSUMPTIONS.md` §9 documents the privacy assessment (hash of content, not PII).

---

## Open Questions

| ID | Question | Default |
|---|---|---|
| Q-F8-01 | Self-hosted Postgres or managed? | **Managed (RDS/Cloud SQL)** at MVP for reduced ops effort; configurable |
| Q-F8-02 | KMS provider | AWS (configurable) |
| Q-F8-03 | User-requested early deletion | **Recommended for v1.1**; documented in COMPLETE_FLOWS Flow 11 |
| Q-F8-04 | Backups encrypted with op-inaccessible key | **No at MVP**; later, integrate with HashiCorp Vault |
| Q-F8-05 | Long-term placeholder projects | Kept indefinitely; placeholder=true flag; excluded from global stats |
| Q-F8-06 | `submission_hash` survival after anonymization | **Yes** (per `_shared/GLOBAL_ASSUMPTIONS.md` §9) |
| Q-F8-07 | Maintenance windows for blocking migrations | **Documented in RUNBOOK**; product approves per migration |
| Q-F8-08 | Restricted access to `privacy_audit_log` | **Yes**; Django Group `compliance_officer` with read-only access |
| Q-F8-09 | Catalog publication: PR + CI or DB-direct? | **PR + CI validates consistency**; CI runs `corpus_ingest --dry-run`, `benchmarks_load --dry-run` |
| Q-F8-10 | system_config table for hot params | **No at MVP** — env vars suffice; revisit if hot reload needed |

---

## Edge Cases

- Migration failure mid-deploy → partial schema. Recovery: restore from latest WAL-backed point; re-run migrate.
- Anonymization job fails on row 150 of 200 → batch rolls back row-by-row inside individual transactions (atomic per row); the other 149 commit fine.
- Lock held > 30 min (orphaned worker) → lock TTL releases it; next Beat tick retries.
- Beat scheduler unavailable → tasks don't run; alert. Operator runs manually via TriggerJobView.
- pgvector extension uninstalled accidentally → migrations re-add via `CREATE EXTENSION IF NOT EXISTS`.
- Project upsert race with two concurrent F2 jobs for same project → ON CONFLICT resolves both to the same row.
- placeholder project for `unknown_<hash>` is reused if the same submission_hash re-occurs after the original was cleaned up (rare; documented).
- Audit log volume spike (operator deletion campaign) → cleanup task processes in batches.

---

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-F8-01 | Schema drift between code and DB | `python manage.py makemigrations --check` in CI |
| R-F8-02 | Anonymization breaking project metrics | Tests assert avg_score equals AVG(score_total) over both anonymized + non-anonymized rows |
| R-F8-03 | Migrations blocking on large tables (ALTER ... ADD NOT NULL) | Use multi-step migrations: add nullable + backfill + add NOT NULL constraint; documented |
| R-F8-04 | Privacy audit log fills disk | TTL + alert |
| R-F8-05 | Backup retention beyond 90 days breaks privacy contract | Backup retention 30 days strictly; restored data older than 90 days must be re-anonymized immediately |

---

## Cross-Validation Log

| Iteration | Discrepancies | Files |
|---|---|---|
| 1 | 0 | First pass, Django-aligned |
| 2 | 0 | — |
| 3 | 0 | — |
| 4 | 0 | Acceptance |

## PRD Alignment Log

| Iteration | Items Checked | Misalignments | Coverage % |
|---|---|---|---|
| 1 | 40 | 0 | 100% |

---

**End of document.**
