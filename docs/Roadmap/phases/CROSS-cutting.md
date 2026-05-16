---
project: Casa Segura
doc_type: phase_index
phase: cross
status: living
last_updated: 2026-05-16
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

Source-of-truth links:

- [Roadmap contract](../README.md) - tickets remain authoritative for status, dependencies, and acceptance criteria.
- [PRD_GENERAL](../../Casa%20Segura%20Formal%20PRDs/PRD_GENERAL.md) - product-level UX, disclaimer, and delivery expectations.
- [FEATURES_MAP](../../Casa%20Segura%20Formal%20PRDs/FEATURES_MAP.md) - core contract-analysis flow and optional project-verification separation.
- [Frontend domain](../domains/Frontend.md) - frontend ticket grouping.
- [Security Privacy domain](../domains/Security%20Privacy.md) - privacy and security ticket grouping.

## Ready Now

- **EPIC-10 FE closure:** **`CS-298`** (operator: connect Vercel + env), then **`CS-299`** (physical device QA checklist). **`CS-295`** is **`done`**; core upload flow tickets **291–297** are **`done`** (see epic).

## FE WORK

- [CS-290](../tickets/CS-290.md) - Landing page — **done**.
- [CS-291](../tickets/CS-291.md) - Upload page with disclaimer gate — **done**.
- [CS-292](../tickets/CS-292.md) - Channel selector component — **done**.
- [CS-293](../tickets/CS-293.md) - Loading state with rotating copy — **done**.
- [CS-294](../tickets/CS-294.md) - Result page with HTML report viewer — **done**.
- [CS-295](../tickets/CS-295.md) - Expired-link page — **done**.
- [CS-296](../tickets/CS-296.md) - Server actions to call backend — **done**.
- [CS-297](../tickets/CS-297.md) - Disclaimer module — **done**.
- [CS-298](../tickets/CS-298.md) - Vercel deploy — **ready** (`frontend/README.md` + `robots`/headers/next.config env gate).
- [CS-299](../tickets/CS-299.md) - Mobile QA pass at 360px — **ready** (`frontend/docs/CS-299-mobile-qa-checklist.md`).

## BE WORK

- [CS-336](../tickets/CS-336.md) - Error-report mechanism.
- [CS-337](../tickets/CS-337.md) - Central disclaimer registry and lint rule.

This lane owns backend-facing support for consistent disclaimers, privacy-safe error reporting, and shared modules that FE consumes.

## INFRA WORK

- [CS-330](../tickets/CS-330.md) - Pipeline observability metrics.
- [CS-331](../tickets/CS-331.md) - Log scrubbing rules.
- [CS-332](../tickets/CS-332.md) - Error tracking SDK with scrubbing.
- [CS-333](../tickets/CS-333.md) - TLS-only transport policy.
- [CS-334](../tickets/CS-334.md) - Secrets rotation runbook.
- [CS-335](../tickets/CS-335.md) - SECURITY.md and disclosure path.

## API / AI CONNECTIONS

- [CS-350](../tickets/CS-350.md) - Billboard OCR extraction.
- [CS-351](../tickets/CS-351.md) - Manual project verification form fallback — **in_progress** (FE shell + validation stub; OCR handoff + backend DTO open).
- [CS-352](../tickets/CS-352.md) - Permit format validator.
- [CS-353](../tickets/CS-353.md) - Reputation lookup interface.
- [CS-354](../tickets/CS-354.md) - Verdict synthesis for project check.
- [CS-355](../tickets/CS-355.md) - Project verification results page — **in_progress** (demo fixtures + CTA; snapshots + real DTO open).
- [CS-356](../tickets/CS-356.md) - `PROJECT_VERIFICATION_ENABLED` feature flag and route enablement — **in_progress** (FE gate + docs; BE/integration open).

Project verification is optional and separate. These tickets must not gate contract upload, analysis, report generation, or delivery.

## Parallel Pick Guidance

- FE can begin once `apps/web` exists. Keep contract analysis primary and project verification optional.
- BE supports disclaimer/error-report contracts that FE and reports can share.
- Infra should start with metrics, log scrubbing, and security runbooks before vendor integrations.
- API / AI project verification remains feature-gated and must not block core contract analysis.

