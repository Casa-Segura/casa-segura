---
id: EPIC-06
name: Rubric Engine & Scoring
phase: 4
status: done
depends_on:
  - EPIC-01
  - EPIC-03
  - EPIC-04
  - EPIC-05
prd_refs:
  - PRD_GENERAL US-03
  - RUBRICA_CONTRATO
  - FEATURES_MAP §4 (F4)
  - BE-SERVICES §4
feature: F4
owner: tbd
tags:
  - casa-segura
  - epic
  - epic-06
  - contract
---

# EPIC-06 — Rubric Engine & Scoring

> **This is the contract**. Everything else feeds this engine or consumes its output. The rubric is the product's intellectual asset; the rest is plumbing.

## Goal

Implement the scoring engine that takes a classified contract (+ extracted economic fields + RAG-retrieved legal citations) and produces a `ContractAnalysis` row with: per-criterion evaluations, findings (each with optional `legal_reference`), category scores, override status, total score, band, and the verdict synthesis.

Delivering [[PRD_GENERAL]] US-03 ("System applies the rubric and produces the score") and US-04 ("System generates the report with verbatim legal citations" — partially; F6 owns the rendering).

## Definition of done

- [x] All 38 criteria from [[RUBRICA_CONTRATO]] §16 have an evaluator that returns a `CriterionEvaluation` for any classified contract
- [x] All 11 overrides from [[RUBRICA_CONTRATO]] §2.2 detect their trigger correctly and force score=0 + band=red when active
- [x] Score aggregation algorithm in [[RUBRICA_CONTRATO]] §10 is implemented and matches the spec line-for-line under property-based testing
- [x] Asymmetric penalty rule ([[RUBRICA_CONTRATO]] §1.1): better-than-benchmark inputs never reduce score below benchmark-equivalent
- [x] Unverifiable handling ([[PRD_GENERAL]] BR-04): missing data scores worst case from the criterion's scale, with justification recorded
- [x] Weight renormalization when criteria don't apply to the detected contract type
- [x] Verdict synthesis prompt produces a 2–3 sentence summary that contains **zero** legal citations not present in the retrieved RAG context ([[PRD_GENERAL]] BR-02, BR-03)
- [x] Every `Finding` produced carries: severity, title, description, optional cited clause, optional `LegalReference` (from RAG), recommendation
- [x] BVA test suite passes for all numeric thresholds (see ticket-level BVA tables)
- [x] [[PRD_GENERAL]] BR-16 (scoring path): criterion specs for `rubric.evaluate_analysis` resolve from `ContractAnalysis.rubric_version` (snapshot at ingest); Celery retries do not silently follow globally active catalog drift ([[CS-358]], [[ADR-0004-versioning]])
- [x] [[PRD_GENERAL]] BR-16 (**canonical F6 HTML/PDF**, `backend/reports/`): footer versions and integrity hash use persisted `ContractAnalysis.rubric_version_id` / corpus / benchmark; per-criterion rows come from **`criterion_evaluations`** (scoring snapshot — no `load_active_specs()`). Category titles/weights in the template use static F6 copy in `section_builders` (not live catalog).
- [x] **Public TTL link ([[CS-247]]) / `delivery.application.report_html`:** `GET /r/<public_short_id>/` delegates to `reports.application.services.html_renderer.generate_report_html` (same BR-16 stamping as Celery HTML/PDF tasks; verified in `backend/tests/test_public_report_route.py`).

## In scope

- Pydantic schemas: `Criterion`, `CriterionEvaluation`, `Finding`, `LegalReference`, `ScoresByCategory`, `OverrideTriggered`, `RubricResult`
- Per-criterion evaluator framework (interface, registry, dispatch by criterion ID)
- All 38 criterion implementations (A1–A6, B1–B9, C1–C7, D1–D6, E1–E9, F1–F5)
- 11 override triggers as first-class detectors
- Score aggregation function (the §10 algorithm)
- Asymmetric penalty enforcement
- Unverifiable bookkeeping
- Verdict synthesis service (consumes findings + RAG, produces summary)
- Synthesis output validation (no hallucinated citations)
- BVA test suite for the high-stakes criteria (B2, B1, B4, all overrides, band boundaries)

## Out of scope (explicit)

- Report rendering — [[EPIC-07-report-generation]]
- LLM provider plumbing — pulled from [[EPIC-00-foundation]] config
- Economic benchmark loading — provided by [[EPIC-05-economic-analysis]]
- Legal corpus retrieval — provided by [[EPIC-03-corpus-rag]]
- Contract type classification — provided by [[EPIC-04-classification]]
- Persistence of the result — uses ORM from [[EPIC-01-persistence]]; no new tables defined here

## Dependencies

- Blocks: [[EPIC-07-report-generation]], [[EPIC-08-multichannel-delivery]] (delivery needs a final analysis)
- Blocked by: [[EPIC-01-persistence]] (schemas), [[EPIC-03-corpus-rag]] (RAG retrieval), [[EPIC-04-classification]] (type + extracted fields), [[EPIC-05-economic-analysis]] (economic numbers)

## Tickets

### Framework and core algorithm

- [[CS-150]] — Pydantic schemas for rubric: Criterion, CriterionEvaluation, Finding, LegalReference, ScoresByCategory
- [[CS-151]] — Override catalog (11 overrides) as first-class constants + their legal anchors
- [[CS-152]] — Score aggregation algorithm per [[RUBRICA_CONTRATO]] §10
- [[CS-153]] — Asymmetric penalty rule enforcement
- [[CS-154]] — Unverifiable handling: worst-case scoring with justification
- [[CS-155]] — Weight renormalization when criteria don't apply
- [[CS-156]] — Band assignment from total score
- [[CS-157]] — Override forcing: any active override → score=0, band=red
- [[CS-158]] — Criterion evaluator framework (interface, registry, dispatch)
- [[CS-358]] — BR-16: resolve rubric catalog for scoring from stamped `ContractAnalysis.rubric_version` (not active singleton by default)

### Per-category evaluators

- [[CS-159]] — Category A evaluators (A1–A6): Legal & formal validity
- [[CS-160]] — Category B evaluators (B1–B9): Economic health
- [[CS-161]] — Category C evaluators (C1–C7): Guarantees
- [[CS-162]] — Category D evaluators (D1–D6): Property risks
- [[CS-163]] — Category E evaluators (E1–E9): Abusive clauses
- [[CS-164]] — Category F evaluators (F1–F5): Transparency

### Synthesis

- [[CS-165]] — Verdict synthesis prompt and service
- [[CS-166]] — Synthesis output validator (no ungrounded citations)

### BVA test suites

- [[CS-167]] — BVA tests for band boundaries (4.9 / 5.0 / 7.9 / 8.0)
- [[CS-168]] — BVA tests for B2 interest rate scale (9 / 10 / 11 / 14 / 19)
- [[CS-169]] — BVA tests for B1 down-payment scale (10 / 15 / 20 / 35)
- [[CS-170]] — BVA tests for all 11 overrides (positive + near-miss negative)
- [[CS-171]] — Property-based test for asymmetric penalty rule

## Risks

| ID | Risk | Mitigation |
|---|---|---|
| R-06-1 | LLM hallucinates citations not in RAG context | Synthesis prompt is strict + [[CS-166]] validator rejects findings whose `legal_reference` doesn't trace to a retrieved chunk |
| R-06-2 | Criterion evaluator drift from spec | Every evaluator cites its [[RUBRICA_CONTRATO]] section; reviewer must verify scale matches exactly |
| R-06-3 | Renormalization bug when many criteria N/A | Property-based test: for every contract type, sum of effective weights = 1.0 within ε |
| R-06-4 | Override silently masked by category averages | [[CS-157]] is the early-return; verified by [[CS-170]] |
| R-06-5 | Spec ambiguity in criteria (e.g. B5 ratio when total price is unknown) | Each evaluator has an explicit "if input missing → unverifiable" branch; [[CS-154]] covers this |

## Notes

- [[RUBRICA_CONTRATO]] is the source of truth. If an evaluator and the rubric disagree, the rubric wins. Surface the discrepancy via PR comment.
- [[BE-SERVICES]] §4.5 reinforces the synthesis discipline: LLM consumes retrieved citations, does not generate them.
- The 38-criterion catalog seeded by [[CS-033]] is what the evaluators look up at runtime; never hard-code criterion metadata in evaluator files.
