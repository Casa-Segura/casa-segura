---
project: Casa Segura
doc_type: phase_index
phase: 4
status: living
last_updated: 2026-05-17
tags:
  - casa-segura
  - roadmap
  - phase-4
---

# Phase 4 - Evaluation Engine

Goal: implement the rubric engine, scoring, overrides, evaluators, synthesis, and boundary-value tests.

Source epic:

- [EPIC-06 - Rubric Engine & Scoring](../EPIC-06-rubric-engine.md)

Source-of-truth links:

- [PRD_F4_MOTOR_RUBRICA](../../Casa%20Segura%20Formal%20PRDs/PRD_F4_MOTOR_RUBRICA.md) - rubric engine requirements.
- [RUBRICA_CONTRATO](../../Casa%20Segura%20Formal%20PRDs/RUBRICA_CONTRATO.md) - criteria, weights, overrides, and scoring philosophy.
- [DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md) - criterion, rubric version, and analysis output entities.
- [F4 analysis plan](../../analysis/F4_motor_rubrica/IMPLEMENTATION_PLAN.md) - implementation breakdown.
- [F4 evaluation coverage](../../analysis/F4_motor_rubrica/EVALUATION_COVERAGE.md) - BVA and property-test coverage expectations.

## Ready Now

No Phase 4 tickets are ready yet. Start after Phase 3 economic summary and Phase 1/2 retrieval/extraction contracts are stable.

## FE WORK

No primary FE tickets live in this phase. FE consumes rubric verdicts, overrides, categories, and finding text in Phase 5 and cross-cutting result pages.

## BE WORK

- [CS-150](../tickets/CS-150.md) - Pydantic schemas for rubric output.
- [CS-151](../tickets/CS-151.md) - Override catalog.
- [CS-152](../tickets/CS-152.md) - Score aggregation algorithm.
- [CS-153](../tickets/CS-153.md) - Asymmetric penalty rule enforcement.
- [CS-154](../tickets/CS-154.md) - Unverifiable handling.
- [CS-155](../tickets/CS-155.md) - Applicability filtering and weight renormalization.
- [CS-156](../tickets/CS-156.md) - Band assignment from total score.
- [CS-157](../tickets/CS-157.md) - Critical override forcing.
- [CS-158](../tickets/CS-158.md) - Criterion evaluator framework.
- [CS-159](../tickets/CS-159.md) - Category A evaluators.
- [CS-160](../tickets/CS-160.md) - Category B evaluators.
- [CS-161](../tickets/CS-161.md) - Category C evaluators.
- [CS-162](../tickets/CS-162.md) - Category D evaluators.
- [CS-163](../tickets/CS-163.md) - Category E evaluators.

## INFRA WORK

**Shipped (2026-05-17):** [[CS-167]]–[[CS-171]] — BVA + Hypothesis coverage in `backend/tests/test_rubric_epic06_bva.py` and `backend/tests/fixtures/overrides/`.

Keep test data traceable to rubric thresholds. Numeric thresholds and overrides need boundary cases, not just happy-path fixtures.

## API / AI CONNECTIONS

- [CS-164](../tickets/CS-164.md) - Category F evaluators and citation wiring.
- [CS-165](../tickets/CS-165.md) - Verdict synthesis prompt and service.
- [CS-166](../tickets/CS-166.md) - Synthesis output validator.

## Parallel Pick Guidance

- BE owns schemas, aggregation, applicability, override forcing, band assignment, dispatcher framework, and deterministic evaluators.
- API / AI owns RAG citation wiring, verdict synthesis, and synthesis validation.
- INFRA WORK owns BVA and property-based tests, especially for numeric thresholds and override behavior.

