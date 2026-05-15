---
id: EPIC-04
name: Classification & Field Extraction
phase: 2
status: backlog
depends_on:
  - EPIC-02
prd_refs:
  - PRD_GENERAL US-02
  - FEATURES_MAP §4 (F2)
  - RUBRICA_CONTRATO §3
feature: F2
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-04
  - stub
---

# EPIC-04 — Classification & Field Extraction

> **Stub.** Epic-level only. Tickets fleshed out in second pass.

## Goal

Identify the contract type (8 enum values + NOT_CLASSIFIABLE), extract project name, extract economic fields (price, down payment, rate, term, monthly payment, charges). Reclassify "purchase disguised as leasing" when the 6 Art. 2 LAF indicators are present.

## Definition of done

- [ ] Classifier assigns one of: CVC, CVP, ARV, ARC, APV, LEA, IVU, FSV, NOT_CLASSIFIABLE
- [ ] Six leasing indicators per Art. 2 LAF detected; reclassification justification recorded in `reclassification_reason`
- [ ] Project name extracted and normalized; Project entity matched or created
- [ ] Economic fields extracted with confidence per field; `unverifiable` set when extraction fails
- [ ] All field outputs feed cleanly into [[EPIC-05-economic-analysis]] and [[EPIC-06-rubric-engine]]

## Tickets (titles only — stubs)

- [[CS-110]] — Classification prompt + few-shot anchors
- [[CS-111]] — Leasing reclassification detector (6 indicators)
- [[CS-112]] — Project name extraction and normalization (chains to [[CS-031]])
- [[CS-113]] — Economic field extraction prompt
- [[CS-114]] — Confidence-per-field schema
- [[CS-115]] — Classification eval set (20 contracts spanning all 8 types)
- [[CS-116]] — Unverifiable bookkeeping for missing fields

## Notes

- [[RUBRICA_CONTRATO]] §3 contract type table is the enum source of truth
- Reclassification is the costliest trap in the market per [[RUBRICA_CONTRATO]] §3
