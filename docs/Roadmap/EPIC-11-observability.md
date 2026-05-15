---
id: EPIC-11
name: Observability, Security & Disclaimers
phase: cross
status: backlog
depends_on:
  - EPIC-00
prd_refs:
  - PRD_GENERAL §5, BR-07
  - ARCHITECTURE §10
feature: cross-cutting
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-11
  - stub
---

# EPIC-11 — Observability, Security & Disclaimers

> **Stub.** Epic-level only. Tickets fleshed out in second pass.

## Goal

Operate the system in production: metrics, logs, alerts, error tracking, TLS, secrets discipline, the disclaimer registry, and the public dispute / error report mechanism per [[PRD_GENERAL]] open question #8.

## Definition of done

- [ ] Metrics emitted: latency per pipeline stage, OCR success rate, leasing reclassification rate, score distribution, override frequency, contract type distribution ([[PRD_GENERAL]] §5)
- [ ] Metrics contain **zero** user-identifying data ([[PRD_GENERAL]] §5)
- [ ] Error tracking captures stack traces but scrubs body content
- [ ] All transport TLS-only
- [ ] Secrets rotation documented
- [ ] SECURITY.md exists with disclosure email and false-positive dispute path
- [ ] Disclaimer registry centralizes every "Esto no es asesoría legal" surface; lint rule prevents string drift

## Tickets (titles only — stubs)

- [[CS-330]] — Metrics emitter (latency, success rates, distributions)
- [[CS-331]] — Log scrubbing rules (no body content, no PII)
- [[CS-332]] — Error tracking integration (e.g. Sentry) with scrubbing
- [[CS-333]] — TLS everywhere policy + enforcement
- [[CS-334]] — Secrets rotation runbook
- [[CS-335]] — SECURITY.md + disclosure email
- [[CS-336]] — Error-report mechanism (per [[PRD_GENERAL]] open question #8)
- [[CS-337]] — Disclaimer registry module + lint rule

## Notes

- [[ARCHITECTURE]] §10 has the privacy posture
- [[PRD_GENERAL]] §5 has the metric list
