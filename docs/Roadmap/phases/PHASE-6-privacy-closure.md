---
project: Casa Segura
doc_type: phase_index
phase: 6
status: living
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - phase-6
---

# Phase 6 - Privacy Closure

Goal: operate privacy invariants over time through scheduled cleanup, anonymization, link expiration, project metric recomputation, and audit records.

Source epic:

- [EPIC-09 - Retention & Privacy Jobs](../EPIC-09-retention-privacy.md)

Source-of-truth links:

- [PRD_F8_PERSISTENCIA_PROYECTO_RETENCION](../../Casa%20Segura%20Formal%20PRDs/PRD_F8_PERSISTENCIA_PROYECTO_RETENCION.md) - persistence, project, and retention requirements.
- [DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md) - retention-sensitive entities and anonymization boundaries.
- [F8 analysis plan](../../analysis/F8_persistencia_retencion/IMPLEMENTATION_PLAN.md) - retention and privacy implementation breakdown.
- [Security Privacy domain](../domains/Security%20Privacy.md) - privacy lane ticket grouping.
- [ADR-0001 - Django backend stack](../../adr/ADR-0001-django-backend-stack.md) - Celery/Redis and Django persistence boundaries.

## Ready Now

- `CS-270` is ready now; see `INFRA WORK`.

## FE WORK

No primary FE tickets live in this phase. FE should coordinate expired-link copy and UI behavior with [CS-295](../tickets/CS-295.md) and [CS-246](../tickets/CS-246.md) so users get a clear recovery path.

## BE WORK

- [CS-271](../tickets/CS-271.md) - Cleanup job for ContractSubmission and OcrJob.
- [CS-272](../tickets/CS-272.md) - Delivery-target erasure job.
- [CS-273](../tickets/CS-273.md) - 90-day anonymization job.
- [CS-274](../tickets/CS-274.md) - Link expiration job.
- [CS-275](../tickets/CS-275.md) - Project average score recomputation.
- [CS-276](../tickets/CS-276.md) - Anonymization audit log row.

## INFRA WORK

- [CS-270](../tickets/CS-270.md) - Scheduler choice and ADR.

This lane defines the operational contract for scheduled jobs: trigger mechanism, manual run path, metrics, retries, and failure visibility.

## API / AI CONNECTIONS

No primary API / AI tickets live in this phase. Retention jobs must still treat OCR text, delivery targets, report content, prompts, and logs as privacy-sensitive data.

## Parallel Pick Guidance

- INFRA WORK starts with `CS-270`; it is ready and independent of app folder work.
- BE owns cleanup SQL, anonymization SQL, link expiration, recomputation logic, and audit writes.
- Security/Privacy review should verify irreversible anonymization behavior and PII-free logs before closure.

