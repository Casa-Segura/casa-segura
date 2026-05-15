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

## Ready Now

- [CS-270](../tickets/CS-270.md) - Choose retention job scheduler and document ADR.

## Tickets

- [CS-270](../tickets/CS-270.md) - Scheduler choice and ADR.
- [CS-271](../tickets/CS-271.md) - Cleanup job for ContractSubmission and OcrJob.
- [CS-272](../tickets/CS-272.md) - Delivery-target erasure job.
- [CS-273](../tickets/CS-273.md) - 90-day anonymization job.
- [CS-274](../tickets/CS-274.md) - Link expiration job.
- [CS-275](../tickets/CS-275.md) - Project average score recomputation.
- [CS-276](../tickets/CS-276.md) - Anonymization audit log row.

## Parallel Pick Guidance

- Infra owner: [CS-270](../tickets/CS-270.md), scheduler contract, manual run path, and metrics shape.
- Backend/Data owner: cleanup SQL, anonymization SQL, link expiration, and recomputation logic.
- Security/Privacy owner: irreversible anonymization behavior, audit rows, and PII-free logs.

