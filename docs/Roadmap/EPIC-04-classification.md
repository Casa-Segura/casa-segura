---
id: EPIC-04
name: Classification & Field Extraction
phase: 2
status: done
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
---

# EPIC-04 — Classification & Field Extraction

## Goal

Identify the contract type (8 enum values + NOT_CLASSIFIABLE), extract project name, extract economic fields (price, down payment, rate, term, monthly payment, charges). Reclassify "purchase disguised as leasing" when the 6 Art. 2 LAF indicators are present.

## Definition of done

- [x] Classifier assigns one of: CVC, CVP, ARV, ARC, APV, LEA, IVU, FSV, NOT_CLASSIFIABLE (CS-110 done — PR-2 wired the PRD §US-01 confidence-band protocol + §8.3 validator).
- [x] Six leasing indicators per Art. 2 LAF detected; reclassification justification recorded in `reclassification_reason` (CS-111 done — PR-3 shipped the severity envelope; PR-6 applies the recommendation onto `ContractAnalysis`).
- [x] Project name extracted and normalized; Project entity matched or created (CS-112 + CS-031 done — PR-4 integration tests against the real DB cover BR-05 collision, BR-06 placeholders, CS-031 AC4 race recovery).
- [x] Economic fields extracted with confidence per field; `unverifiable` set when extraction fails (CS-113 + CS-114 + CS-116 done — PR-1 schemas, PR-5 AMBIGUOUS signal, PR-6 aggregator wiring with status precedence AMBIGUOUS > INVALID > NOT_PRESENT > PRESENT).
- [x] All field outputs feed cleanly into [[EPIC-05-economic-analysis]] and [[EPIC-06-rubric-engine]] (PR-6 orchestrator + `POST /api/v1/internal/classify`; CS-115 CI gate added PR-7).

## Tickets (closed)

- [[CS-110]] — Classification prompt + few-shot anchors → **done** 2026-05-17
- [[CS-111]] — Leasing reclassification detector (6 indicators) → **done** 2026-05-17
- [[CS-112]] — Project name extraction and normalization (chains to [[CS-031]]) → **done** 2026-05-17
- [[CS-113]] — Economic field extraction prompt → **done** 2026-05-17
- [[CS-114]] — Confidence-per-field schema → **done** 2026-05-17
- [[CS-115]] — Classification eval set (≥20 contracts) + CI gate → **done** 2026-05-17
- [[CS-116]] — Unverifiable bookkeeping for missing fields → **done** 2026-05-17

## Notes

- [[RUBRICA_CONTRATO]] §3 contract type table is the enum source of truth.
- Reclassification is the costliest trap in the market per [[RUBRICA_CONTRATO]] §3.
- F2 §5.1 columns landed via `platform_core/0005_classification_f2_fields.py` (PR-0). EPIC-01's DoD bullet for project upsert is ticked there.
- The F2 orchestrator lives at `backend/classification/application/orchestrator.py::F2Orchestrator`. Public QA surface: `POST /api/v1/internal/classify` gated by `X-Internal-Token` against `settings.INTERNAL_API_TOKEN`.
- Eval gate workflow: `.github/workflows/classification-eval.yml`. Triggers manual / nightly cron / PR label `eval:classification`. Baseline appendix captured in CS-115 once `OPENROUTER_API_KEY` is configured on the repo.
