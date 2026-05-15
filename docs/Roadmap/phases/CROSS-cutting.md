---
project: Casa Segura
doc_type: phase_index
phase: cross
status: living
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - cross-cutting
---

# Cross-Cutting Work

Goal: track frontend, observability/security, and optional project verification work that cuts across the phase roadmap.

Source epics:

- [EPIC-10 - Frontend Web App](../EPIC-10-frontend.md)
- [EPIC-11 - Observability, Security & Disclaimers](../EPIC-11-observability.md)
- [EPIC-12 - Project Verification](../EPIC-12-project-verification.md)

## Ready Now

- [CS-290](../tickets/CS-290.md) - Build mobile-first landing page.

## Frontend Web App

- [CS-290](../tickets/CS-290.md) - Landing page.
- [CS-291](../tickets/CS-291.md) - Upload page with disclaimer gate.
- [CS-292](../tickets/CS-292.md) - Channel selector component.
- [CS-293](../tickets/CS-293.md) - Loading state with rotating copy.
- [CS-294](../tickets/CS-294.md) - Result page with HTML report viewer.
- [CS-295](../tickets/CS-295.md) - Expired-link page.
- [CS-296](../tickets/CS-296.md) - Server actions to call backend.
- [CS-297](../tickets/CS-297.md) - Disclaimer module.
- [CS-298](../tickets/CS-298.md) - Vercel deploy.
- [CS-299](../tickets/CS-299.md) - Mobile QA pass at 360px.

## Observability, Security, and Disclaimers

- [CS-330](../tickets/CS-330.md) - Pipeline observability metrics.
- [CS-331](../tickets/CS-331.md) - Log scrubbing rules.
- [CS-332](../tickets/CS-332.md) - Error tracking SDK with scrubbing.
- [CS-333](../tickets/CS-333.md) - TLS-only transport policy.
- [CS-334](../tickets/CS-334.md) - Secrets rotation runbook.
- [CS-335](../tickets/CS-335.md) - SECURITY.md and disclosure path.
- [CS-336](../tickets/CS-336.md) - Error-report mechanism.
- [CS-337](../tickets/CS-337.md) - Central disclaimer registry and lint rule.

## Optional Project Verification

- [CS-350](../tickets/CS-350.md) - Billboard OCR extraction.
- [CS-351](../tickets/CS-351.md) - Manual project verification form fallback.
- [CS-352](../tickets/CS-352.md) - Permit format validator.
- [CS-353](../tickets/CS-353.md) - Reputation lookup interface.
- [CS-354](../tickets/CS-354.md) - Verdict synthesis for project check.
- [CS-355](../tickets/CS-355.md) - Project verification results page.
- [CS-356](../tickets/CS-356.md) - `PROJECT_VERIFICATION_ENABLED` deployment gate.

## Parallel Pick Guidance

- Frontend can begin once `apps/web` exists. Keep contract analysis primary and project verification optional.
- Observability/security work should start with metrics/logging and scrubbing contracts, then vendor integrations.
- Project verification must not gate contract upload or analysis.

