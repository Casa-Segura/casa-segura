# Evaluation Coverage — F2: Contract Classification & Structured Extraction

> Generated: 2026-05-15
> Source: `PRD_F2_CLASIFICACION.md` + cross-cutting decisions in `../_shared/GLOBAL_ASSUMPTIONS.md`
> Stack: Django 5.2 LTS + DRF + Celery.

---

## PRD Contradictions

No contradictions internal to PRD_F2 were detected after the Step 1 re-read.

Cross-PRD items that touch F2 are recorded in `../_shared/GLOBAL_ASSUMPTIONS.md`:
- §4 — Project name normalization rule (F2 vs DOMAIN_MODEL). MODERATE; resolved by adopting F2's stricter rule and accepting the risk of collapsing distinct projects.
- §7 — Reclassification threshold (4 of 6 vs 6 of 6). MODERATE; resolved at 4 of 6, configurable.

---

## Coverage Matrix

| PRD Requirement | Covered By | Status |
|---|---|---|
| US-01: classify into 9 types | `IMPLEMENTATION_PLAN.md` Story US-01, `SOLUTION_DIAGRAMS.md` §2.1, `COMPLETE_FLOWS.md` Flow 1 | COVERED |
| US-02: extract & normalize project name | `IMPLEMENTATION_PLAN.md` Story US-02 + `ProjectNameNormalizer`, `COMPLETE_FLOWS.md` Flow 6 | COVERED |
| US-03: reclassify CVP→LEA | `IMPLEMENTATION_PLAN.md` Story US-03, `SOLUTION_DIAGRAMS.md` §2.3, `COMPLETE_FLOWS.md` Flow 3 | COVERED |
| US-04: extract economic fields | `IMPLEMENTATION_PLAN.md` Story US-04, `COMPLETE_FLOWS.md` Flow 5 | COVERED |
| US-05: detect 12 legal elements | `IMPLEMENTATION_PLAN.md` Story US-05 (within §8.1 response) | COVERED |
| US-06: NOT_CLASSIFIABLE clean reject | `COMPLETE_FLOWS.md` Flow 4 | COVERED |
| BR-01 strict 9 outcomes | `ContractType` enum, parser rejects out-of-enum | COVERED |
| BR-02 reclassify only from CVC/CVP/APV | `ClassificationService` conditional | COVERED |
| BR-03 4-of-6 threshold | `LEASING_RECLASSIFICATION_THRESHOLD` env var | COVERED |
| BR-04 no personal data persisted | Pydantic Result has no name/DUI/NIT fields, DB columns don't allow them | COVERED |
| BR-05 normalization rules | `ProjectNameNormalizer.normalize()` | COVERED |
| BR-06 unknown placeholder per submission | `COMPLETE_FLOWS.md` Flow 6 | COVERED |
| BR-07 economic raw passed to F5 | `ClassificationDone` envelope; F2 does not persist economics | COVERED |
| BR-08 monthly→annual conversion | `ExtractEconomicStep` post-processing | COVERED |
| BR-09 element flags are hints | Documented in `DESIGN_PATTERNS.md` Hint-Provider | COVERED |
| BR-10 P95 ≤ 20 s, 2 attempts | NFR metrics + retry semantics | COVERED |
| BR-11 idempotency keys per step | Each `LlmStep` has its key suffix | COVERED |
| BR-12 no conversational dialog | Service never enqueues a clarifier; reject on ambiguity | COVERED |
| Data model `ContractAnalysis` columns | `ENTITY_RELATIONSHIP_DIAGRAM.md` + `IMPLEMENTATION_PLAN.md` Stage 7 | COVERED |
| Data model `ClassificationJob` | `IMPLEMENTATION_PLAN.md` Stage 6 with migration | COVERED |
| Data model `Project` upsert | `ProjectRepository.upsert` design pattern doc | COVERED |
| API `/v1/internal/classify` | `IMPLEMENTATION_PLAN.md` Story US-01 endpoint table, Flow 8 | COVERED |
| Prompts §8.1/§8.2/§8.3/§8.4/§8.5 | `IMPLEMENTATION_PLAN.md` Stage 5 verbatim in `prompts.py` | COVERED |
| NFR P50 ≤ 8 s | Stage 12 metrics | COVERED |
| NFR cost ≤ $0.05 USD per analysis | Cost metric `f2_cost_cents_total` | COVERED |
| NFR successful rate > 95% | Tracked by `f2_classification_outcome_total{outcome}` | COVERED |
| NFR reclassification FP < 2% | Metric `f2_reclassification_total` with QA labels; calibration tracked outside this plan | COVERED (instrumented) |
| Integration: F1→F2 queue | `INTERACTION_DIAGRAMS.md` Component Overview + `IMPLEMENTATION_PLAN.md` Stage 10 | COVERED |
| Integration: F2→F4 + F2→F5 | `ClassificationDone` envelope, two consumer groups | COVERED |

---

## Critical Points

1. **LLM JSON reliability**. The `JsonResponseParser` with fence-stripping and balanced-brace extraction is the critical defense against malformed model output. Without it, the failure rate doubles. CI tests exercise multiple malformed-output scenarios.
2. **Reclassification correctness**. False reclassification of a legitimate CVP into LEA shocks the user (it forces a different rubric category). False non-reclassification of disguised leasing is the headline product harm. The 4-of-6 threshold is the chosen trade-off; needs calibration on real Salvadoran contracts in QA.
3. **Project upsert race**. Two simultaneous submissions of the same project must converge on one row. `INSERT ... ON CONFLICT` is the technical guarantee; the implementation plan documents it.
4. **`evidence_snippet` leak**. The LLM returns clause text in evidence snippets. F2 must NOT persist snippets in its own tables (only `reclassification_indicators` JSONB stores them via `IndicatorDetection.evidence`). F4 later persists snippets as part of `findings.evidence_clause_snippet`, subject to 90-day anonymization (BR-00 of F8).
5. **Cost ceiling**. Up to five LLM calls per submission. Worst case at $0.05 USD limit per analysis must be tested in QA before production.

---

## Open Questions

**[Q-F2-01]: Should the LLM produce JSON via `response_format=json_object` or rely on prompting alone?**
Source: PRD §10 Q-5.
Impact: Reliability of parsing.
Resolution: **Assumed**: Use `response_format={"type": "json_object"}` when the chosen model supports it; rely on the parser recovery otherwise.

**[Q-F2-02]: Should project-name normalization be even more aggressive (e.g., stemming, plural collapse)?**
Source: PRD §10 Q-2 + `../_shared/GLOBAL_ASSUMPTIONS.md` §4.
Impact: Higher recall on the project entity at the cost of collapsing genuinely distinct projects.
Resolution: **Assumed (no stemming at MVP)**. The current rules are aggressive enough. Document the risk in the report's project note.

**[Q-F2-03]: How are bilingual (Spanish + English) contracts handled?**
Source: PRD §10 Q-7.
Impact: A Salvadoran contract with English boilerplate (common in some commercial leases) passes F1's language check. F2 may classify it correctly.
Resolution: **Assumed**: Process normally. The LLM is multilingual; classification accuracy is preserved.

**[Q-F2-04]: Should classification confidence be shown to the user?**
Source: PRD §10 Q-6.
Impact: Transparency vs. confusion.
Resolution: **Assumed (no)**. Confidence is internal only.

**[Q-F2-05]: When the LLM fails parseable JSON but the response has confidence > 0.85 textually, do we accept?**
Source: PRD §10 Q-5.
Impact: Reduces failed_classification at the cost of robustness.
Resolution: **Assumed (no)**. Parse-failure is a system error; `failed_classification` is the right state. Retry once before failing.

**[Q-F2-06]: Should the system detect contracts modified between submissions (variants)?**
Source: PRD §10 Q-3.
Impact: User pays for a re-analysis after editing one paragraph.
Resolution: **Assumed (no at MVP)**. Hash-based dedup only.

**[Q-F2-07]: Is the 12-element list final?**
Source: PRD §10 Q-4.
Impact: Future additions need schema change for `elements_detected` JSONB.
Resolution: **Assumed yes for MVP**. JSONB is forward-compatible; new flags can be added without migration.

**[Q-F2-08]: Strict redaction of party names before sending text to LLM?**
Source: PRD §10 Q-8.
Impact: Strict mode requires NER preprocessing that may corrupt the text.
Resolution: **Assumed (no)**. The LLM sees party names during processing; F2 does not persist them. The privacy contract is "we don't store your data", not "the LLM never sees it".

---

## Edge Cases to Validate

- Contract presented as `CVP` but with only 3 of 6 LAF indicators → no reclassification, but the indicators are persisted for F4 to surface as yellow-finding hints.
- Contract presented as `LEA` directly → no reclassification attempt (skip §8.4 step).
- Project name with emojis, e.g. "🏠 Residencial Las Palmeras" → normalization strips the emoji and produces `las palmeras`.
- Project name in all caps with hyphens, e.g. "URBANIZACIÓN-LAS-PALMERAS" → normalization yields `urbanizacion las palmeras`, then drops the leading "urbanizacion" → `las palmeras`. ✓ matches the simple-form project.
- Two `LEA` contracts of the same project → both upsert into the same `Project` row; `total_analyses` reaches 2 (after F8 cron).
- `monthly_rate_pct = 0.015` (no `annual_rate_pct`) → derived `annual_rate_pct ≈ 0.1956`, note set.
- `interest_calculation_base = total_balance` → flag persisted in `EconomicFieldsRaw`; F4 evaluates B7 and may trigger `art_12_lpc` override.
- Contract written in second-person ("comprarás", "pagarás") vs. third-person ("el comprador") → classifier accuracy unaffected (prompt uses Spanish vocabulary).
- Confidence exactly 0.65 → boundary; current rule: < 0.65 → reject; ≥ 0.65 < 0.85 → validate. Boundary documented.
- Confidence exactly 0.85 → boundary; ≥ 0.85 → accept directly.
- LLM returns `"contract_type": "OTHER"` (out-of-enum) → treated as NOT_CLASSIFIABLE.
- Concurrent two submissions of the same hash hitting F2 (F1 dedup race lost): the second processing finds `contract_analysis.contract_type` already set; the worker checks and short-circuits.

---

## Risks

| ID | Risk | Level | Mitigation |
|---|---|---|---|
| R-F2-01 | LLM output drift (model upgrade) | Architecture | Pin model name; QA regression suite on a sample of labeled contracts before unlocking new defaults |
| R-F2-02 | Project name collisions (over-normalized) | Product | Documented in F8's `Project.metadata`; ops can split a project manually if a complaint comes in |
| R-F2-03 | Cost surge from a malicious huge-text submission | Operations | Token cap on the prompt input (`MAX_PROMPT_INPUT_TOKENS=32000` per call); reject text above |
| R-F2-04 | Race between two submissions of new project | Execution | `INSERT ... ON CONFLICT` upsert |
| R-F2-05 | Reclassification false positive vs. negative | Product | Threshold configurable; QA labeled set for calibration |
| R-F2-06 | LLM refuses JSON output | Architecture | Parser recovery; retry once; double-fail → `LLM_PARSE_FAILED` |

---

## Cross-Validation Log

| Iteration | Discrepancies Found | Files Corrected | Details |
|---|---|---|---|
| 1 | 0 | — | First pass after Django realignment of `_shared/GLOBAL_ASSUMPTIONS.md`. All F2 files generated in Django/DRF style from the start. |
| 2 | 0 | — | Re-read pass: every entity in ERD appears in SOLUTION_DIAGRAMS class diagram and at least one sequence diagram. Every API endpoint in COMPLETE_FLOWS.md has an entry in IMPLEMENTATION_PLAN.md. Every design pattern reflected in the implementation plan. |
| 3 | 0 | — | Cross-reference verification: field names, types, command/query names, endpoint paths, response codes consistent across all files. |
| 4 | 0 | — | Final acceptance pass. Clean. |

---

## PRD Alignment Log

| Iteration | PRD Items Checked | Misalignments Found | Corrections Applied | Coverage % |
|---|---|---|---|---|
| 1 | 30 (6 US + 12 BR + 12 NFR/integration/data items) | 0 | — | 100% |

All 6 user stories, 12 business rules, the data-model section, the integration points, the prompts, and the NFRs from `PRD_F2` are represented in at least one artifact. The 8 open questions from PRD_F2 §10 are surfaced in this file with assumed defaults.

---

**End of document.**
