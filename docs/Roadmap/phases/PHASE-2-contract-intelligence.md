---
project: Casa Segura
doc_type: phase_index
phase: 2
status: living
last_updated: 2026-05-16
# Phase 2 BE/API kickoff: CS-110 + CS-114 first-pass shipped in 2026-05-16 batch.
tags:
  - casa-segura
  - roadmap
  - phase-2
---

# Phase 2 - Contract Intelligence

Goal: classify the contract, extract key fields, normalize project identity, and produce confidence/unverifiable metadata for downstream economics and rubric work.

Status legend: ☑ done · ◐ in progress · ☐ backlog · ✗ blocked/cut.

Source epic:

- [EPIC-04 - Classification & Field Extraction](../EPIC-04-classification.md)

Source-of-truth links:

- [PRD_F2_CLASIFICACION](../../Casa%20Segura%20Formal%20PRDs/PRD_F2_CLASIFICACION.md) - classification, extraction, confidence, and unverifiable behavior.
- [PRD_GENERAL](../../Casa%20Segura%20Formal%20PRDs/PRD_GENERAL.md) - product-level user stories and business rules.
- [DOMAIN_MODEL](../../Casa%20Segura%20Formal%20PRDs/DOMAIN_MODEL.md) - contract analysis fields and project identity.
- [F2 analysis plan](../../analysis/F2_clasificacion/IMPLEMENTATION_PLAN.md) - implementation breakdown and flow assumptions.
- [ADR-0001 - Django backend stack](../../adr/ADR-0001-django-backend-stack.md) - backend boundary for services, DTOs, and persistence.

## Ready Now

Phase 1 ingestion + corpus retrieval contracts are in place (commit `d613c2d`):

- `POST /api/v1/submissions/` returns `extracted_text_language` + `extracted_text_token_count` per submission, with the text held only in-memory through the extractor (CS-057 invariant — never persisted).
- `LegalCitationService.retrieve_legal_basis(finding=…)` returns ≥0 citations via `POST /api/v1/corpus/retrieve/`.

**2026-05-16 — Phase 2 first-pass complete (7 of 7 tickets shipped):**

All Phase 2 tickets have code shipped under `backend/classification/`.

Status of the dependency chain:

1. ☑→◐ **CS-110** entry point shipped (prompt + few-shot anchors + classifier wired to OpenRouter client).
2. ☑→◐ **CS-114** DTO shape shipped (`ExtractedFields` 19 fields, `ConfidenceBand`, `ContractExtraction`, `REQUIRED_FIELDS_BY_TYPE`).
3. ☑→◐ **CS-111** leasing reclassification detector (6 Art. 2 LAF indicators, threshold 4/6, scope = purchase-side types per PRD §8.4).
4. ☑→◐ **CS-112** project name normalization + linkage (extractor + linker with collision/upsert policy; implements CS-031 AC4 per ADR-0003).
5. ☑→◐ **CS-113** economic field extraction (per-type prompts + value coercion + extractor).
6. ☑→◐ **CS-116** unverifiable bookkeeping aggregator (`ExtractionStatus` + `AggregatedExtraction` + warning precursor for `interest_calculation_base_unfavorable`).
7. ☑→◐ **CS-115** classification eval set (31 synthetic BR-07-safe cases + `eval_classification` harness command).

**All 7 tickets stay `in_progress`** for one of two reasons:
- Live OpenRouter exercise still needed (CS-110/111/112/113/115).
- Downstream wiring still needed (CS-116 → CS-137 persistence; CS-114 → `elements_detected` flag map).

**DDD layering verified clean**: `classification/domain/*` has zero infra imports (`django.*`, `httpx`, `requests`, `shared.llm.*`).

**Phase 2 done-blockers** (in priority order):
1. **Orchestrator service** to wire CS-110 → CS-111 → CS-112 → CS-113 → CS-116 into a single classification pipeline (no ticket yet — likely belongs to a new EPIC-04 closeout ticket or CS-137).
2. **CS-137** persistence: `AggregatedExtraction` → `ContractAnalysis.economic_summary` JSONB.
3. **Live eval run**: `python manage.py eval_classification --threshold 0.95` against real `OPENROUTER_API_KEY` → if it passes thresholds, flips CS-110/111/112/113/115 to `done`.
4. **CI wiring** of the eval harness as a gate (CS-115 AC4).

Upstream notes:

- CS-110 needs a working OpenRouter client + access to extracted text — both shipped in commit `d613c2d` (`shared/llm/openrouter.py`, in-memory text passed by `upload_service.ingest_upload`). The classifier should plug into the same client used by CS-054.
- CS-112's accent/case normalization piggybacks on the function shipped under CS-031 (Phase-0 in_progress); the upsert AC explicitly belongs to this ticket.

## FE WORK

No primary FE tickets live in this phase. FE depends on the API contract outputs here for later upload/result experiences in [Cross-Cutting Work](CROSS-cutting.md).

## BE WORK

- ◐ [CS-112](../tickets/CS-112.md) - Project name extraction and normalization. *(2026-05-16: `ProjectNameExtractor` + `ProjectLinker` shipped under `backend/classification/{domain,application}/project_*.py`. Placeholder hash = `unknown_<sha256[:8](text)>`; orchestrator can override via `placeholder_seed=submission_hash`. Collision resolution uses `select_for_update` + IntegrityError catch for races. **CS-031 AC4 implemented here** per ADR-0003. 3/4 ACs; AC4 orchestrator wiring of `ContractAnalysis.project_id` pending.)*
- ◐ [CS-114](../tickets/CS-114.md) - Classification confidence and extraction field schema. *(2026-05-16: `ExtractedFields` (19 optional fields), `ConfidenceLevel`/`ConfidenceBand`, `ContractExtraction`, `REQUIRED_FIELDS_BY_TYPE` policy table covering all 9 ContractType values shipped under `backend/classification/domain/` + `backend/classification/application/extraction_policy.py`. 3/4 ACs; AC4 `elements_detected` flag map pending.)*
- ◐ [CS-116](../tickets/CS-116.md) - Unverifiable bookkeeping for missing fields. *(2026-05-16: `ExtractionStatus` StrEnum + `EconomicSlot` + `AggregatedExtraction` + pure `aggregate_extraction()` shipped under `backend/classification/{domain,application}/`. BVA boundary `confidence < 0.5` → NOT_PRESENT verified (0.49 → NOT_PRESENT, 0.50 → PRESENT). `warning_precursors` emits `interest_calculation_base_unfavorable` when base=total_balance + rate missing. 3/3 ACs ticked; stays `in_progress` until CS-137 wires `AggregatedExtraction` into `ContractAnalysis.economic_summary` JSONB.)*

## INFRA WORK

- ◐ [CS-115](../tickets/CS-115.md) - Classification eval set. *(2026-05-16: `backend/fixtures/classification_eval_cases.yaml` ships **31 synthetic cases** (CVC 3, CVP 5, ARV 4, ARC 3, APV 3, LEA 3, IVU 3, FSV 3, NOT_CLASSIFIABLE 4) including 2 leasing-BVA cases (3-of-6 stays CVP / 4-of-6 → LEA) + 1 borderline-confidence variant. Harness command `python manage.py eval_classification` with `--dry-run`/`--threshold`/`--out` flags. Threshold defaults from PRD F2 §9 (macro_accuracy_min 0.95, NC precision_min 0.90, reclass FP_max 0.02, FN_max 0.10). 3/4 ACs; AC4 CI wiring is separate work.)*

Keep eval fixtures versioned and privacy-safe. Coordinate with CI conventions from Phase 0 before adding expensive model-backed checks.

## API / AI CONNECTIONS

- ◐ [CS-110](../tickets/CS-110.md) - Classification prompt and few-shot anchors. *(2026-05-16: `ContractType` enum (9 values from PRD §8.1), Spanish system prompt + `FEW_SHOT_ANCHORS` (one synthetic BR-07-safe anchor per type), `ContractClassifier.classify()` wired to `shared.llm.openrouter.OpenRouterClient` at `temperature=0.1`. 2/N ACs ticked; live eval blocked by CS-115; persistence by CS-114 confidence orchestration.)*
- ◐ [CS-111](../tickets/CS-111.md) - Leasing reclassification detector. *(2026-05-16: `LeasingReclassificationDetector` + `LeasingIndicators` (6 Art. 2 LAF booleans per PRD §8.4) + `LeasingReclassificationResult` (model_validator enforces "only LEA on reclassification") shipped. Threshold = 4/6 per PRD BR-03, overridable via constructor. **Important per-PRD scope correction:** detector runs over **purchase-side** types `{CVC, CVP, APV}` to catch disguised-purchase-as-lease, not over lease-side types. 3/10 ACs; orchestrator wiring + live LLM eval pending.)*
- ◐ [CS-113](../tickets/CS-113.md) - Economic field extraction prompt. *(2026-05-16: `EconomicFieldExtractor` + per-type prompt registry (`economic_prompts.py`) + `value_coercion.py` (money/int/pct/periodicity/interest-base/currency coercers) shipped. Dedicated few-shots for CVC/CVP/ARV/LEA; APV/ARC/IVU/FSV fall back to CVP anchor (richest field menu). Per-field validation failures demote to `unverifiable` rather than crashing. 5/5 ACs ticked in code but stays `in_progress` until CS-115 live eval runs.)*

## Parallel Pick Guidance

- API / AI owns prompts, few-shot anchors, leasing reclassification, and economic extraction.
- BE owns normalized project linkage, confidence schemas, and unverifiable payload shape.
- INFRA WORK owns eval fixtures and coverage across all contract types.

