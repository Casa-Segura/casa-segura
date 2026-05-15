# Design Patterns — F4: Rubric Engine

> Generated: 2026-05-15

---

## Patterns Applied

### Specification-driven Evaluator

**Why it fits:** Each of the 38 criteria is a self-contained specification (`Criterion` row) carrying its applicability, scale, prompt, override binding, and weight. The evaluator is a generic loop that knows nothing about specific criteria — it reads the spec and runs it. Adding a 39th criterion is a data-only change.

**What it covers:** `CriterionEvaluator.evaluate(criterion, ctx)`; the loop in `RubricEvaluationService.evaluate_criteria`.

**Implementation location:** `rubric/application/services/criterion_evaluator.py`, criteria YAML loaded by seed migration into `criterion` table.

---

### Weighted Aggregate with Renormalization

**Why it fits:** Some criteria do not apply to a given contract type, and some categories may be empty. Treating non-applicable as zero would unfairly penalize honest contracts. Renormalizing weights against the actually-applicable set is the right and PRD-mandated behavior.

**Implementation:** `ScoreCalculator.compute_category_score`, `compute_total`. Both reduce over the applicable subset and re-divide by the sum of weights.

---

### Override (Veto)

**Why it fits:** Some clauses are so harmful that an average score is misleading. The PRD encodes 11 such conditions. The pattern: detected override → vetoes the average → forces `score_total=0, band=red`.

**Implementation:** `ScoreCalculator.compute_total(scores, overrides)`; the overrides list flows from each `CriterionEvaluation.override_triggered`.

---

### Cite or Stay Silent (consumed from F3)

**Why it fits:** F4 must not invent legal references. The pattern is enforced by:
1. F3's strict threshold (returns empty when below cutoff)
2. F4's prompt explicitly forbids the model from generating citations
3. `FindingFactory` only attaches what F3 returns; tags `market_based` or `unverifiable_legal` on empty

**Implementation:** `FindingFactory.from_evaluation` — never modifies `legal_basis` after F3 returns.

---

### Symmetric Asymmetric Penalty

**Why it fits:** A favorable value (e.g., 5% down payment when 10% is the benchmark) must score 10, not penalize. The rubric's per-criterion scale encodes this. F4's evaluator passes the LLM the scale verbatim; the LLM applies it. We do not implement penalty math; the scale itself is the rule.

---

### Bounded Concurrency (Semaphore)

**Why it fits:** ~32 LLM calls per analysis at unbounded parallelism would slam OpenRouter and trigger rate-limits. A semaphore caps concurrent calls at 8. This balances total latency (32/8 = 4 waves ≈ 4 × 5 s ≈ 20 s) against provider stability.

**Implementation:** `asyncio.Semaphore(LLM_RUBRIC_CONCURRENCY)` inside `RubricEvaluationService.evaluate_criteria`.

---

### Watermark Barrier (F4 ↔ F5)

**Why it fits:** F4 and F5 run in parallel; F4's economic criteria need F5's `economic_summary`. Two coordination options:
- Celery chord — typed but cumbersome with two independent task chains
- DB watermark — F5 sets `contract_analysis.economic_summary`; F4 polls

**Decision:** the DB watermark. Simpler, observable, naturally idempotent. F4 polls with backoff up to `F4_ECONOMIC_BARRIER_TIMEOUT_SECONDS=60`. If F5 still hasn't written, F4 evaluates economic criteria as unverifiable (BR-15).

---

### Two-step LLM call (criterion + executive summary)

**Why it fits:** The per-criterion calls produce detail; one final call produces the user-facing summary. Keeping the summary as a separate call lets us prompt it differently ("tú", calm, max 3 sentences).

**Implementation:** Separate prompt in `rubric/infrastructure/llm/prompts.py::EXECUTIVE_SUMMARY_PROMPT`.

---

### Anti-corruption Layer (LLM output)

**Why it fits:** LLM JSON is unreliable. F4 reuses F2's `JsonResponseParser` recovery (fence strip, balanced-brace extraction) + Pydantic validation. On parse failure → one retry → mark criterion unverifiable.

**Implementation:** `CriterionEvaluator._parse_response` delegates to `shared/infrastructure/llm/parser.py`.

---

## Patterns Considered and Rejected

### Single LLM mega-prompt covering all 38 criteria

Tempting: one big response. Rejected because: token budget exceeds limits, idempotency-key isolation per criterion is lost, one parse error fails everything, no per-criterion retry granularity, and the PRD §10 OQ-7 explicitly says "single criterion per call".

### Sub-classing per criterion

Instead of a generic loop driven by `Criterion` data, write a class per criterion. Rejected because: 38 classes is repetitive; adding a 39th becomes a code change; the spec-driven loop is testable and clean.

### Two-tier rubric (fast classifier first)

Pre-classify clauses by topic (with cheap embeddings) and only call LLM on relevant criteria. Rejected because: complexity not justified at MVP, all 38 criteria are required regardless, the cost ceiling is already met.

### Caching evaluations across analyses

Tempting: a clause similar to a prior one might reuse its evaluation. Rejected because: false-positive cross-contamination of findings (different contracts = different context), audit trail muddied, and the cost is already within budget.

---

**End of document.**
