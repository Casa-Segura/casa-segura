---
project: Casa Segura
doc_type: phase_index
phase: 4
status: living
last_updated: 2026-05-15
tags:
  - casa-segura
  - roadmap
  - phase-4
---

# Phase 4 - Evaluation Engine

Goal: implement the rubric engine, scoring, overrides, evaluators, synthesis, and boundary-value tests.

Source epic:

- [EPIC-06 - Rubric Engine & Scoring](../EPIC-06-rubric-engine.md)

## Framework and Core Algorithm

- [CS-150](../tickets/CS-150.md) - Pydantic schemas for rubric output.
- [CS-151](../tickets/CS-151.md) - Override catalog.
- [CS-152](../tickets/CS-152.md) - Score aggregation algorithm.
- [CS-153](../tickets/CS-153.md) - Asymmetric penalty rule enforcement.
- [CS-154](../tickets/CS-154.md) - Unverifiable handling.
- [CS-155](../tickets/CS-155.md) - Applicability filtering and weight renormalization.
- [CS-156](../tickets/CS-156.md) - Band assignment from total score.
- [CS-157](../tickets/CS-157.md) - Critical override forcing.
- [CS-158](../tickets/CS-158.md) - Criterion evaluator framework.

## Evaluators

- [CS-159](../tickets/CS-159.md) - Category A evaluators.
- [CS-160](../tickets/CS-160.md) - Category B evaluators.
- [CS-161](../tickets/CS-161.md) - Category C evaluators.
- [CS-162](../tickets/CS-162.md) - Category D evaluators.
- [CS-163](../tickets/CS-163.md) - Category E evaluators.
- [CS-164](../tickets/CS-164.md) - Category F evaluators and citation wiring.

## Synthesis and Tests

- [CS-165](../tickets/CS-165.md) - Verdict synthesis prompt and service.
- [CS-166](../tickets/CS-166.md) - Synthesis output validator.
- [CS-167](../tickets/CS-167.md) - BVA tests for score bands.
- [CS-168](../tickets/CS-168.md) - BVA tests for B2 interest rate scale.
- [CS-169](../tickets/CS-169.md) - BVA tests for B1 down-payment scale.
- [CS-170](../tickets/CS-170.md) - BVA tests for all overrides.
- [CS-171](../tickets/CS-171.md) - Property-based test for asymmetric penalty.

## Parallel Pick Guidance

- Backend core owner: schemas, aggregation, applicability, override forcing, band assignment, and dispatcher framework.
- Backend/AI owner: per-category evaluators, RAG citation wiring, and synthesis validation.
- QA owner: BVA and property-based tests.

