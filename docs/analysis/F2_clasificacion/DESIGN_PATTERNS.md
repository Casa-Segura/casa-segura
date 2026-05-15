# Design Patterns — F2: Contract Classification & Structured Extraction

> Generated: 2026-05-15
> Cross-cutting patterns: `../_shared/GLOBAL_ASSUMPTIONS.md` §12. F2-specific patterns below.

---

## Patterns Applied

### Two-Phase classifier (Self-validating LLM)

**Why this pattern fits:** The PRD demands strict classification (no compound types) and rejects ambiguity. A single LLM call with `confidence` is unreliable on borderline contracts. The two-phase approach — accept if confident, retry-and-validate if medium, reject if low — gives the system a calibrated rejection mechanism without conversational disambiguation.

**What it covers:** the `ClassificationService.classify()` flow that calls §8.1 first, optionally §8.3 second, and decides accept/validate/reject based on confidence thresholds.

**What it does NOT cover:** the threshold values themselves (0.65 and 0.85) are configurable; they are not constant magic numbers.

**Implementation location:** `classification/application/services/classification_service.py::_run_classification`, `_run_validation`.

---

### Hint-Provider (not Decision-Maker)

**Why this pattern fits:** F2 produces `elements_detected` flags about clauses, and `EconomicFieldsRaw` with confidence/evidence. F4 (rubric) consumes these as **acceleration hints** to focus its own prompts — but is allowed to disagree. This avoids cascading errors: a false flag in F2 does not necessarily become a false finding in F4.

**What it covers:** the contract between F2 and F4 — `ClassificationDone` envelope ships hints; F4's per-criterion prompt includes the hints in the prompt context but instructs the model "use only the contract text as authority; the hints below may be incorrect".

**What it does NOT cover:** the criterion-evaluation logic itself (F4-owned).

**Implementation location:** `classification/application/contracts/messages.py::ClassificationDone`, consumed by F4.

---

### Strategy (LLM prompt selection)

**Why this pattern fits:** F2 has up to five distinct LLM steps with different prompts and different output shapes. Encapsulating each step as a callable that takes `extracted_text` and returns a typed Pydantic result keeps the service code linear and lets each prompt evolve independently. Each step also has its own idempotency-key suffix and metrics labels.

**What it covers:**
- `ClassifyAndExtractStep` (§8.1/§8.2 prompt → `RawClassificationOutput`)
- `ValidateClassificationStep` (§8.3 prompt → `RawClassificationOutput`)
- `DetectLeasingStep` (§8.4 prompt → `LeasingIndicators`)
- `ExtractEconomicStep` (§8.5 prompt → `EconomicFieldsRaw`)

Each step has a shared `Protocol`:

```python
class LlmStep(Protocol):
    name: ClassificationStep
    response_model: type[BaseModel]

    def build_prompt(self, *, extracted_text: str, ctx: dict) -> ChatMessages: ...
    def parse(self, raw: dict) -> BaseModel: ...
```

**Implementation location:** `classification/infrastructure/llm/steps/{classify_and_extract,validate,detect_leasing,extract_economic}.py`.

---

### Pipes & Filters (intra-feature)

**Why this pattern fits:** within F2 itself there is a linear chain: classify → maybe validate → maybe leasing → maybe economic → elements → project → publish. Encoding it as small, composable functions in `ClassificationService.classify()` makes it easy to short-circuit any stage (e.g., `NOT_CLASSIFIABLE` skips all later stages).

**Implementation location:** `classification_service.py` body.

---

### Upsert with partial index (Project matching)

**Why this pattern fits:** Multiple submissions of the same project race to create the same `Project` row. We need a single atomic upsert keyed on `normalized_name`. Postgres `INSERT ... ON CONFLICT (normalized_name) DO UPDATE` handles this in one statement.

**What it covers:**
```sql
INSERT INTO project (canonical_name, normalized_name, first_seen, last_analyzed, total_analyses)
VALUES ($1, $2, NOW(), NOW(), 0)
ON CONFLICT (normalized_name)
DO UPDATE SET last_analyzed = NOW(), canonical_name = EXCLUDED.canonical_name
RETURNING id, (xmax = 0) AS was_inserted;
```

`xmax = 0` lets the application know whether it created a fresh row (and may want to emit a "new project detected" event) or hit an existing one.

**Implementation location:** `classification/infrastructure/django/repositories.py::ProjectRepository.upsert`.

---

### Anti-Corruption Layer (LLM output validation)

**Why this pattern fits:** LLMs are unreliable producers of strict JSON. The integration boundary validates the raw response against a Pydantic model and treats malformed output as an error to retry (transient) or to fail (after max attempts).

**What it covers:**
- `RawClassificationOutput` Pydantic model with strict types and validators
- `JsonResponseRecoveryPolicy`: if the response is wrapped in ```json``` fences, strip them; if it contains pre/post text, attempt to extract the first balanced `{...}` block; only after recovery validate with Pydantic.
- If validation fails twice in a row, mark `failed_classification`.

**Implementation location:** `classification/infrastructure/llm/parser.py`, `classification/infrastructure/llm/steps/base.py`.

---

## Patterns Considered and Rejected

### Conversational disambiguation

Tempting: "ask the user a clarifying question" when confidence is medium. Rejected because the PRD §10 OQ-12 explicitly forbids dialog. Casa Segura is a one-shot product. Disambiguation by retry is the correct response.

### Single mega-prompt (classify + leasing + economic + elements in one call)

The PRD §8.1 already combines classification with `elements_detected`. We considered combining leasing and economic into the same call too. Rejected because:
1. Reclassification logic is conditional on the initial type — single-call breaks this.
2. Output token budget for one mega-response would exceed common model limits.
3. Idempotency-key isolation is harder when one network call covers four logical steps.

### Cache classification by `submission_hash`

Tempting: skip the LLM if we have classified the same hash before. Rejected because F1 already deduplicates by hash; if the hash matches a prior analysis, the user never reaches F2.

### Embedding-based contract-type pre-filter

Train embeddings on labeled contract types and skip the LLM when distance to a known cluster is small. Rejected at MVP because: no labeled dataset; the LLM call is the cheap-enough cost; the precision/recall trade-off needs careful evaluation that delays delivery.

---

**End of document.**
