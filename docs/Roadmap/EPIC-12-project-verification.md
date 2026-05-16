---
id: EPIC-12
name: Project Verification (Billboard OCR + Form Fallback)
phase: cross
status: in_progress
depends_on:
  - EPIC-00
  - EPIC-01
prd_refs:
  - ARCHITECTURE §5 (Flow 1 — legacy hackathon framing)
  - STATUS T007–T009
  - STATUS R1 (panic button: form fallback)
feature: separate flow (not in F1–F8)
owner: tbd
research_refs:
  - GENERATED-RESEARCH-create-ocr-documentation-2026-05-11
tags:
  - casa-segura
  - epic
  - epic-12
---

> **In progress.** [[CS-356]] / [[CS-351]] / [[CS-355]] have **partial** frontend shells under `frontend/src/app/verificacion-proyecto/` (feature-flagged; stubs until OCR/verdict backend lands). Remaining tickets carry OCR, validation, reputation, and synthesis scope.

Notes (2026-05-16): Route hub + manual form shell + demo result page are mergeable without backend; photograph entry and real verdict DTO remain open.

## Goal

Optional, **separate entry point** from contract analysis. User photographs the project's billboard or fills a manual form. System extracts developer name, project name, permit, address; runs lightweight checks (permit format sanity, reputation signals if available, blacklist if a curated one exists). Returns a verdict that the user can act on **independently** — the user is not forced to upload a contract afterward, and they can come back to do contract analysis at a different time.

Per user direction: **contract analysis is NOT gated on this flow**. The two are related but independent.

## Rationale (why a separate epic)

The formal PRDs ([[PRD_GENERAL]], [[FEATURES_MAP]]) do not include billboard/project verification — they cover only contract analysis. The intent in [[STATUS]] (hackathon framing) and [[ARCHITECTURE]] §5 (Flow 1) is preserved here as an optional capability that complements the main product without being a precondition for it.

## Definition of done

- [ ] Two entry surfaces: (a) photograph the billboard, (b) manual form
- [ ] OCR path extracts: developer, project, permit, address
- [ ] OCR failure path falls back to the form ([[STATUS]] R1 panic button)
- [ ] Permit format sanity check (regex on Salvadoran formats)
- [ ] Reputation lookup if a provider is configured (else skip with a note)
- [ ] Verdict shape mirrors the green/yellow/red model
- [ ] Result page tells the user they can also analyze a contract — but does not require it
- [ ] No `session_id` gate — contract analysis is reachable from any entry point

## In scope

- Billboard OCR via vision LLM
- Manual form fallback
- Permit format regex
- Optional reputation lookup (gated by env config)
- Verdict synthesis (small — much simpler than [[EPIC-06-rubric-engine]])

## Out of scope

- Forcing users into contract analysis after this flow
- Curated developer blacklist (post-MVP if added at all — see [[STATUS]] R6 and [[PRD_GENERAL]] BR-11)
- Persistent storage of billboard images
- Reputation API integration if no provider configured

## Tickets

- [[CS-350]] — Billboard OCR with vision LLM
- [[CS-351]] — Form fallback UI/route
- [[CS-352]] — Permit format regex + validator
- [[CS-353]] — Reputation lookup interface (provider-pluggable)
- [[CS-354]] — Verdict synthesis for project check
- [[CS-355]] — Result page with optional CTA to contract analysis
- [[CS-356]] — Disable / enable gates via env (`PROJECT_VERIFICATION_ENABLED`)

## Notes

- [[GENERATED-RESEARCH-create-ocr-documentation-2026-05-11]] — primary OCR reference for this epic per user direction
- [[ARCHITECTURE]] §5 has the original Flow 1 data flow (now read as the *project verification* flow, not as a gate to contract analysis)
- [[STATUS]] R1 documents the panic button: form replaces OCR if vision validation fails
- Blacklist explicitly excluded — see [[PRD_GENERAL]] BR-11
