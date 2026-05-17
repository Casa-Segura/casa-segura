---
id: EPIC-09
name: Retention & Privacy Jobs
phase: 6
status: in_progress
depends_on:
  - EPIC-01
  - EPIC-08
prd_refs:
  - PRD_GENERAL US-07, BR-01
  - FEATURES_MAP §4 (F8 part 2)
  - RUBRICA_CONTRATO §12.3
feature: F8 (part 2)
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-09
---

# EPIC-09 — Retention & Privacy Jobs

> **Progress (2026-05-17):** Transient cleanup (**[[CS-271]]**), delivery-target wipe (**[[CS-272]]**), and link expiry (**[[CS-274]]**) ship under `platform_core.worker.retention` + django-celery-beat migration `0006_retention_beat_schedules`. **[[CS-273]]** (anonymize), **[[CS-275]]** (project metrics), and **[[CS-276]]** (audit rows) remain.

## Goal

Operate the privacy invariants over time: cleanup of transient submissions / OCR jobs at their `expires_at`, erasure of `DeliveryRequest.target_value_encrypted` after delivery, 90-day anonymization of `ContractAnalysis`, link expiration, and recomputation of `Project.avg_score` after anonymizations.

## Definition of done

- [ ] Cron jobs run on a schedule and are idempotent
- [x] `ContractSubmission` and `OcrJob` rows past `expires_at` are deleted
- [x] `DeliveryRequest.target_value_encrypted` cleared after successful delivery
- [ ] `ContractAnalysis` older than 90 days is anonymized per [[PRD_GENERAL]] US-07 (target hash cleared, economic summary bucketed)
- [x] `delivery_status = expired` set on links past `link_expires_at`
- [ ] `Project.avg_score` recomputed when underlying analyses change
- [ ] Anonymization is irreversible and recorded in an audit log row (count + timestamp, no PII)

## Tickets (titles only — stubs)

- [[CS-270]] — Job scheduler choice (APScheduler vs cron-in-container) + ADR
- [[CS-271]] — Cleanup job for `ContractSubmission` and `OcrJob`
- [[CS-272]] — Delivery-target erasure job
- [[CS-273]] — 90-day anonymization job
- [[CS-274]] — Link expiration job
- [[CS-275]] — `Project.avg_score` recomputation
- [[CS-276]] — Anonymization audit log row

## Notes

- BVA boundary: `created_at = NOW() - 89d23h59m` (NOT anonymized) vs `NOW() - 90d00m01s` (IS anonymized)
- [[RUBRICA_CONTRATO]] §12.3 sets the bucket discretization rules for `economic_summary` anonymization
