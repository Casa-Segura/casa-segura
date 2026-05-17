---
id: EPIC-07
name: Report Generation
phase: 5
status: in_progress
depends_on:
  - EPIC-06
  - EPIC-05
prd_refs:
  - PRD_GENERAL US-04
  - FEATURES_MAP §4 (F6)
  - RUBRICA_CONTRATO §11
feature: F6
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-07
  - stub
---

# EPIC-07 — Report Generation

> **Stub.** Epic-level only. Tickets fleshed out in second pass.

## Goal

Compose the responsive HTML report per [[RUBRICA_CONTRATO]] §11 and render to PDF for email or download. Report is **regenerated on demand** from `ContractAnalysis`; never persisted ([[PRD_GENERAL]] BR-01).

## Definition of done

- [x] HTML template covers the 8 sections in [[RUBRICA_CONTRATO]] §11.1
- [x] PDF renderer (WeasyPrint or similar) produces a legible PDF at print density
- [x] Disclaimer in header and footer ([[PRD_GENERAL]] BR-07)
- [x] Override box prominent when override active
- [x] Findings rendered with collapsible legal-reference card per [[BE-SERVICES]] §5
- [x] Art. 1686 CC warning always shown ([[PRD_GENERAL]] open question #5 — recommended yes)
- [x] Rubric and corpus version visible in footer
- [ ] Mobile renders correctly from 360px width

## Tickets (titles only — stubs)

- [[CS-200]] — HTML template skeleton with 8 sections
- [[CS-201]] — Section: Header (logo, ID, type, project)
- [[CS-202]] — Section: Overall verdict + override box
- [[CS-203]] — Section: Economic analysis with bench bar
- [[CS-204]] — Section: Breakdown by category (collapsible)
- [[CS-205]] — Section: Highlighted findings
- [[CS-206]] — Section: Referenced legal bases
- [[CS-207]] — Section: Suggested actions (3 blocks)
- [[CS-208]] — Section: Footer with disclaimer + versions
- [[CS-209]] — PDF rendering via WeasyPrint
- [[CS-210]] — Mobile-first CSS QA at 360px

## Notes

- The example finding format in [[RUBRICA_CONTRATO]] §11.2 is the visual reference for [[CS-205]]
- "Tú" register, not "usted" ([[STATUS]] D8)
