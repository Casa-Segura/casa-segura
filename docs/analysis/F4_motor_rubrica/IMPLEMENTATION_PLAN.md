# Implementation Plan — F4: Rubric Engine

> Generated: 2026-05-15
> Stack: Django 5.2 LTS + Celery + Postgres
> Module: `rubric/`
> Depends: F2, F3, F5, F8.

---

## Directory Structure

```
rubric/
├── domain/
│   ├── entities.py           # RubricVersion, Criterion, CriterionEvaluation, CategoryScore, Finding, FullAnalysisResult, RawEvaluation
│   ├── enums.py              # Band, Severity, OverrideCode
│   ├── exceptions.py
│   └── protocols.py
├── application/
│   ├── commands.py           # EvaluateContractAnalysis, AbsorbEconomicSummary, PersistEvaluation
│   ├── queries.py            # GetCriteriaForRubricVersion, GetActiveRubricVersion, GetAnalysisForEvaluation
│   ├── handlers/
│   │   ├── rubric_handlers.py
│   │   └── persistence_handlers.py
│   └── services/
│       ├── rubric_evaluation_service.py
│       ├── criterion_evaluator.py
│       ├── score_calculator.py
│       └── finding_factory.py
├── infrastructure/
│   ├── django/
│   │   ├── apps.py
│   │   ├── models.py         # RubricVersionModel, CriterionModel (declared here; FK to platform tables)
│   │   ├── repositories.py
│   │   ├── serializers.py
│   │   ├── views.py          # InternalEvaluateCriterionView, InternalListCriteriaView
│   │   ├── urls.py
│   │   ├── management/commands/rubric_seed.py
│   │   └── migrations/
│   │       ├── 0001_initial.py        # rubric_version, criterion tables
│   │       └── 0002_seed_v1_0_0.py    # data migration loading YAML
│   ├── celery/
│   │   └── rubric_tasks.py            # @shared_task evaluate_analysis, absorb_economic_summary
│   ├── llm/
│   │   └── prompts.py                 # CRITERION_SYSTEM_PROMPT, EXECUTIVE_SUMMARY_PROMPT
│   └── redis/
│       └── stream_consumer.py
└── criteria/
    └── v1.0.0.yaml                    # The 38 criteria, source of seed migration
```

---

## App Configuration

```python
# rubric/infrastructure/django/apps.py
from django.apps import AppConfig

class RubricConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rubric.infrastructure.django"
    label = "rubric"
    verbose_name = "Casa Segura — Rubric Engine"
```

---

## Domain Entities (Pydantic)

```python
# rubric/domain/entities.py
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from rubric.domain.enums import Band, Severity, OverrideCode


class RubricVersion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: str
    released_at: datetime
    criteria_count: int
    categories: dict[str, float]
    changelog: str | None = None
    is_active: bool = False
    created_at: datetime


class Criterion(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    rubric_version: str
    category: Literal["A","B","C","D","E","F"]
    title: str
    description: str
    weight_in_category: float = Field(gt=0, le=100)
    applicable_types: list[str]
    legal_anchor: list[str] = []
    override_code: OverrideCode | None = None
    evaluation_prompt: str
    scoring_scale: dict
    worst_case_when_unverifiable: float = 4.0
    depends_on_economic: list[str] = []  # used to short-circuit unverifiable per BR-15


class CriterionEvaluation(BaseModel):
    criterion_id: str
    category: Literal["A","B","C","D","E","F"]
    applicable: bool
    evaluated: bool
    unverifiable: bool
    score: float = Field(ge=0.0, le=10.0)
    weight_in_category: float
    override_triggered: OverrideCode | None = None
    justification: str
    evidence_snippet: str | None = None  # ≤ 500 chars; truncated at edge


class CategoryScore(BaseModel):
    category: Literal["A","B","C","D","E","F"]
    category_name: str
    weight_global: float
    weight_effective: float
    score: float
    criteria_count_total: int
    criteria_count_applicable: int
    criteria_count_unverifiable: int


class Finding(BaseModel):
    id: str  # F-NNN
    severity: Severity
    title: str
    description: str
    evidence_clause_snippet: str | None = None
    legal_basis: list = []  # list[LegalReference] from F3
    recommendation: str
    related_criterion_id: str
    anchors_to_override: OverrideCode | None = None
    tags: list[str] = []


class FullAnalysisResult(BaseModel):
    analysis_id: UUID
    score_total: float
    band: Band
    override_triggered: list[OverrideCode] = []
    scores_by_category: list[CategoryScore]
    criterion_evaluations: list[CriterionEvaluation]
    findings: list[Finding]
    findings_count: int
    critical_findings_count: int
    unverifiable_count: int
    executive_summary: str
    rubric_version: str
    corpus_version: str
    benchmark_version: str


class RawEvaluation(BaseModel):
    """Raw LLM output schema; validated then mapped to CriterionEvaluation."""
    criterion_id: str
    score: float = Field(ge=0.0, le=10.0)
    unverifiable: bool = False
    override_triggered: str | None = None
    justification: str
    evidence_snippet: str | None = None
    should_emit_finding: bool = True
    finding_severity: Literal["critical","red","yellow","green","unverifiable"] | None = None
    recommendation: str
```

## Enumerations

```python
# rubric/domain/enums.py
from django.db import models


class Band(models.TextChoices):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    NOT_ANALYZABLE = "not_analyzable"


class Severity(models.TextChoices):
    CRITICAL = "critical"
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"
    UNVERIFIABLE = "unverifiable"


class OverrideCode(models.TextChoices):
    ART_1605_CC = "art_1605_cc"
    ART_1613_CC = "art_1613_cc"
    ART_1644_CC = "art_1644_cc"
    ART_1425_CC = "art_1425_cc"
    ART_3_IVU_FAMILY_HOMESTEAD = "art_3_ivu_family_homestead"
    ART_5_LPC_NON_WAIVABLE = "art_5_lpc_non_waivable"
    ART_12_LPC = "art_12_lpc"
    ART_13_LPC = "art_13_lpc"
    ART_18_LPC_BLANK_SIGNATURE = "art_18_lpc_blank_signature"
    ART_17H_LPC_ARBITRATION = "art_17h_lpc_arbitration"
    ART_58_FSV = "art_58_fsv"
```

## Commands and Queries

```python
# rubric/application/commands.py
from uuid import UUID
from pydantic import BaseModel
from rubric.domain.entities import FullAnalysisResult


class EvaluateContractAnalysis(BaseModel):
    analysis_id: UUID


class AbsorbEconomicSummary(BaseModel):
    analysis_id: UUID


class PersistEvaluation(BaseModel):
    analysis_id: UUID
    result: FullAnalysisResult
```

```python
# rubric/application/queries.py
from shared.domain.entities.cqrs import BaseGetAttributes, BaseFilterAttributes, Query


class GetActiveRubricVersion(BaseGetAttributes, Query): pass

class GetCriteriaForRubricVersion(BaseFilterAttributes, Query):
    rubric_version: str
    applicable_to_types: list[str] | None = None

class GetAnalysisForEvaluation(BaseGetAttributes, Query):
    analysis_id: str
```

## New Dependencies

- Already covered by F1/F2/F3; F4 adds nothing new beyond YAML loader for criteria seed.

---

## Story: US-01 — Evaluate applicable criteria

Files to create: `rubric/application/services/{rubric_evaluation_service, criterion_evaluator}.py`, `rubric/infrastructure/llm/prompts.py`, the criterion table seed migration.

### Reference Code

```python
# rubric/application/services/criterion_evaluator.py
import asyncio
from rubric.domain.entities import Criterion, CriterionEvaluation, RawEvaluation
from rubric.infrastructure.llm.prompts import CRITERION_SYSTEM_PROMPT


class CriterionEvaluator:
    def __init__(self, *, llm, parser, settings):
        self.llm = llm
        self.parser = parser
        self.settings = settings

    async def evaluate(self, *, criterion: Criterion, ctx: dict, analysis_id: str) -> CriterionEvaluation:
        # Short-circuit on F5 economic dependencies
        if criterion.depends_on_economic and any(
            ctx["economic_summary"].get("fields_extracted", {}).get(f) is None
            for f in criterion.depends_on_economic
        ):
            return CriterionEvaluation(
                criterion_id=criterion.id, category=criterion.category,
                applicable=True, evaluated=False, unverifiable=True,
                score=criterion.worst_case_when_unverifiable, weight_in_category=criterion.weight_in_category,
                justification=f"Economic value {criterion.depends_on_economic} not extractable from contract.",
            )

        prompt = self._build_prompt(criterion, ctx)
        key = f"{analysis_id}:f4:crit:{criterion.id}"
        try:
            raw = await self.llm.chat_completion_json(
                model=self.settings.LLM_RUBRIC_MODEL,
                messages=prompt,
                idempotency_key=key,
                timeout=self.settings.LLM_RUBRIC_TIMEOUT_PER_CRITERION_SECONDS,
                temperature=self.settings.LLM_RUBRIC_TEMPERATURE,
            )
            evaluation = self.parser.parse(raw, RawEvaluation)
        except Exception:
            # one retry then unverifiable
            try:
                raw = await self.llm.chat_completion_json(...)
                evaluation = self.parser.parse(raw, RawEvaluation)
            except Exception:
                return CriterionEvaluation(
                    criterion_id=criterion.id, category=criterion.category,
                    applicable=True, evaluated=False, unverifiable=True,
                    score=criterion.worst_case_when_unverifiable,
                    weight_in_category=criterion.weight_in_category,
                    justification="LLM evaluation failed; marked unverifiable.",
                )

        score = criterion.worst_case_when_unverifiable if evaluation.unverifiable else evaluation.score
        snippet = (evaluation.evidence_snippet or "")[:500] or None
        return CriterionEvaluation(
            criterion_id=criterion.id, category=criterion.category,
            applicable=True, evaluated=not evaluation.unverifiable, unverifiable=evaluation.unverifiable,
            score=score, weight_in_category=criterion.weight_in_category,
            override_triggered=evaluation.override_triggered, justification=evaluation.justification,
            evidence_snippet=snippet,
        )

    def _build_prompt(self, criterion: Criterion, ctx: dict) -> list[dict]:
        user = criterion.evaluation_prompt.format(
            contract_text=ctx["extracted_text"][:30000],  # cap input tokens
            economic_summary=ctx["economic_summary"],
            elements_detected=ctx["elements_detected"],
        )
        return [
            {"role": "system", "content": CRITERION_SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ]
```

### Files to Create

- `rubric/application/services/{rubric_evaluation_service,criterion_evaluator,score_calculator,finding_factory}.py`
- `rubric/infrastructure/llm/prompts.py` (CRITERION_SYSTEM_PROMPT verbatim per PRD §8.1; EXECUTIVE_SUMMARY_PROMPT per §8.3)
- `rubric/criteria/v1.0.0.yaml` — 38 criteria definitions
- `rubric/infrastructure/django/migrations/0001_initial.py` and `0002_seed_v1_0_0.py`
- `rubric/infrastructure/celery/rubric_tasks.py`

### API Endpoints (internal only)

| Method | URL | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/v1/internal/rubric/evaluate-criterion` | `HasInternalAuthHeader` | `{criterion_id, rubric_version, contract_text, contract_type, economic_fields, elements_detected}` | 200 `{score, unverifiable, override_triggered, justification, evidence_snippet, tokens_consumed, cost_estimate_cents, elapsed_ms}` |
| GET | `/v1/internal/rubric/version/{version}` | `HasInternalAuthHeader` | — | 200 `[Criterion]` |

### Test Cases

- [ ] 32 criteria all evaluated → score, band computed
- [ ] One criterion returns unverifiable=true → score forced to `worst_case_when_unverifiable`
- [ ] One criterion returns `override_triggered` → score_total=0
- [ ] Multiple overrides → all recorded, score_total=0
- [ ] LLM transient failure → retry → success
- [ ] LLM parse failure twice → criterion marked unverifiable
- [ ] Concurrency cap 8 enforced
- [ ] Per-criterion timeout
- [ ] Total wall time over 5 min → fail
- [ ] Renormalization: A6 not applicable → A1..A5 weights re-normalized

---

## Story: US-02 — Override detection

ScoreCalculator-driven. No separate flow; the override list is collected from the evaluations and passed to `compute_total`.

### Test Cases

- [ ] 0 overrides → score = weighted average
- [ ] 1 override → score = 0, band = RED, finding[critical] visible first
- [ ] 3 overrides → all in `override_triggered` list, score = 0
- [ ] Override triggered with score=10 (rare) → still forces total 0

---

## Story: US-03 — F3 anchoring (cite-or-stay-silent)

`FindingFactory.from_evaluation` calls F3. Empty results → tag. F3 already tested in F3 plan.

### Test Cases

- [ ] F3 returns 3 references → first 3 attached
- [ ] F3 returns 0 references AND criterion has legal_anchor → tag `unverifiable_legal`
- [ ] F3 returns 0 references AND criterion has NO legal_anchor → tag `market_based`
- [ ] F3 down → handled as 0 results with `unverifiable_legal`

---

## Story: US-04 — Category score with renormalization

`ScoreCalculator.compute_category_score`:

```python
def compute_category_score(evals: list[CriterionEvaluation], category_meta: dict) -> CategoryScore:
    total_weight = sum(e.weight_in_category for e in evals)
    if total_weight == 0:
        return CategoryScore(category=..., score=0.0, criteria_count_applicable=0, ...)
    score = sum(e.score * e.weight_in_category for e in evals) / total_weight
    return CategoryScore(score=score, ...)
```

### Test Cases

- [ ] A1..A5 apply, A6 not → renormalized over 85% of original weights
- [ ] All A criteria apply → standard average
- [ ] All A criteria unverifiable → score = worst_case avg ≈ 4
- [ ] Empty category (0 applicable) → omitted, not 0

---

## Story: US-05 — Total score with category renormalization

```python
def compute_total(category_scores: list[CategoryScore], global_weights: dict, overrides: list[OverrideCode]) -> tuple[float, Band]:
    if overrides:
        return 0.0, Band.RED
    applicable = {cs.category: cs for cs in category_scores if cs.criteria_count_applicable > 0}
    weight_sum = sum(global_weights[c] for c in applicable.keys())
    if weight_sum == 0:
        return 0.0, Band.NOT_ANALYZABLE
    score = sum(applicable[c].score * (global_weights[c] / weight_sum) for c in applicable.keys())
    score = round(score, 1)
    return score, assign_band(score)

def assign_band(score: float) -> Band:
    if score >= 8.0: return Band.GREEN
    if score >= 5.0: return Band.YELLOW
    return Band.RED
```

### Test Cases

- [ ] All 6 categories apply → standard total
- [ ] Category C has no applicable criteria → renormalized over remaining
- [ ] Override fires → total = 0
- [ ] Boundary 7.9 → yellow, 8.0 → green, 4.9 → red, 5.0 → yellow

---

## Story: US-06 — Findings ordering

`FindingFactory.emit_findings` sorts by `(severity_rank, -weight_in_category)` where rank is `{critical:0, red:1, yellow:2, green:3, unverifiable:4}`.

### Test Cases

- [ ] Mixed severities → ordered correctly
- [ ] Within severity, higher weight first
- [ ] Critical findings count matches `critical_findings_count`

---

## Story: US-07 — Persist analysis

`ContractAnalysisRepository.persist_evaluation(analysis_id, result)`: single UPDATE transaction with all 11 fields plus `processing_completed_at` on the submission.

### Test Cases

- [ ] All 11 columns persisted in one tx
- [ ] Retry of the persist on connection drop succeeds (idempotent by `analysis_id`)
- [ ] Partial persist not possible (transaction atomic)

---

## Story: US-08 — Executive summary

Final LLM call. The prompt receives aggregates (no raw contract text). On LLM failure, fallback to a deterministic template:

```python
DEFAULT_SUMMARIES = {
    Band.GREEN: "Este contrato luce favorable en general. La banda verde indica que tanto las cifras como las cláusulas están dentro de lo aceptable. Aún así, llévalo a tu abogado antes de firmar.",
    Band.YELLOW: "Este contrato tiene cifras o cláusulas que necesitan negociación antes de firmar. Lleva los hallazgos a tu abogado y a la otra parte.",
    Band.RED: "Este contrato te expone a riesgo serio. La banda roja indica desviaciones importantes contra ti. No firmes sin asesoría legal y exigir cambios.",
}
```

### Test Cases

- [ ] LLM summary ≤ 3 sentences
- [ ] No legal citations in summary
- [ ] Override mentioned when present
- [ ] LLM failure → deterministic fallback

---

## Part 2 — Staged Execution Plan

### Codebase Alignment Rules

- Django 5.2 LTS + DRF
- `RubricVersionModel` and `CriterionModel` declared in `rubric/infrastructure/django/models.py` (this is one of the **catalog tables** which can live in `rubric`; F8 owns only the central business + transient tables)
- `INSTALLED_APPS`: `"rubric.infrastructure.django"`
- Celery tasks `rubric.evaluate_analysis`, `rubric.absorb_economic_summary`
- All env vars under `LLM_RUBRIC_*` and `F4_*`

### Stage Overview

| # | Stage | Deliverable |
|---|---|---|
| 1 | Domain entities + enums + exceptions | Pydantic + TextChoices |
| 2 | Commands, queries | CQRS |
| 3 | Handlers | Plain functions |
| 4 | Service classes | RubricEvaluationService, CriterionEvaluator, ScoreCalculator, FindingFactory |
| 5 | Django models + migrations | RubricVersionModel, CriterionModel + initial migration |
| 6 | Criteria YAML + seed migration | `rubric/criteria/v1.0.0.yaml` + 0002_seed |
| 7 | Repositories | CriterionRepository, RubricVersionRepository, augment ContractAnalysisRepository |
| 8 | LLM prompts | prompts.py |
| 9 | Celery tasks | rubric_tasks.py |
| 10 | Stream consumer daemon | XREADGROUP from classification.to_rubric_and_economics group rubric |
| 11 | Internal endpoints | InternalEvaluateCriterionView + InternalListCriteriaView + URLs |
| 12 | Tests | pytest with respx-mocked LLM, fixture criteria |
| 13 | Observability | Prometheus metrics |

### Stage 5: Django models

```python
# rubric/infrastructure/django/models.py
from django.contrib.postgres.fields import ArrayField
from django.db import models
from rubric.domain.enums import OverrideCode


class RubricVersionModel(models.Model):
    version = models.TextField(primary_key=True, help_text="Semver of the rubric.")
    released_at = models.DateTimeField(auto_now_add=True, help_text="Publication time.")
    criteria_count = models.IntegerField(help_text="Number of criteria in this version.")
    categories = models.JSONField(help_text="Global weights per category, e.g. {A:.20,B:.30,...}.")
    changelog = models.TextField(null=True, blank=True, help_text="Notes vs prior version.")
    is_active = models.BooleanField(default=False, help_text="Whether this is the version new analyses use.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created timestamp.")

    class Meta:
        db_table = "rubric_version"

    def __str__(self) -> str:
        return f"RubricVersion {self.version}"


class CriterionModel(models.Model):
    id = models.TextField(help_text="Stable id (A1, B2, E7, ...).")
    rubric_version = models.ForeignKey(RubricVersionModel, on_delete=models.PROTECT, related_name="criteria", help_text="Owning rubric version.")
    category = models.CharField(max_length=1, help_text="Category A..F.")
    title = models.TextField(help_text="Short title.")
    description = models.TextField(help_text="What is assessed.")
    weight_in_category = models.DecimalField(max_digits=4, decimal_places=2, help_text="Percentage within the category.")
    applicable_types = ArrayField(models.CharField(max_length=16), help_text="Contract types this criterion applies to.")
    legal_anchor = ArrayField(models.TextField(), default=list, help_text="Slugs F3 prefers for retrieval.")
    override_code = models.CharField(max_length=64, choices=OverrideCode.choices, null=True, blank=True, help_text="If this criterion triggers an override, which code.")
    evaluation_prompt = models.TextField(help_text="Prompt template in Spanish; supports {contract_text}, {economic_summary}, {elements_detected} placeholders.")
    scoring_scale = models.JSONField(help_text="Discrete 0..10 scale with textual criteria per band.")
    worst_case_when_unverifiable = models.DecimalField(max_digits=3, decimal_places=1, default=4.0, help_text="Score added when criterion is unverifiable.")
    depends_on_economic = ArrayField(models.TextField(), default=list, help_text="EconomicSummary field names this criterion depends on (for short-circuit).")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created timestamp.")

    class Meta:
        db_table = "criterion"
        unique_together = [("id", "rubric_version")]
        indexes = [
            models.Index(fields=["rubric_version"], name="idx_criterion_rubric"),
            models.Index(fields=["category"], name="idx_criterion_category"),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(category__in=["A","B","C","D","E","F"]), name="criterion_category_valid"),
        ]

    def __str__(self) -> str:
        return f"Criterion {self.id} ({self.rubric_version})"
```

### Stage 9 — Celery task

```python
# rubric/infrastructure/celery/rubric_tasks.py
from celery import shared_task

@shared_task(name="rubric.evaluate_analysis", bind=True, max_retries=2)
def evaluate_analysis(self, analysis_id: str) -> None:
    """Main F4 task: orchestrate evaluation + scoring + persistence + F6 dispatch."""
    from rubric.application.services.rubric_evaluation_service import RubricEvaluationService
    service = RubricEvaluationService(...)
    import asyncio
    asyncio.run(service.evaluate(analysis_id=analysis_id))

@shared_task(name="rubric.absorb_economic_summary")
def absorb_economic_summary(analysis_id: str) -> None:
    """Hook for the chord callback; no-op if not needed."""
    pass
```

### Stage 13 — Metrics

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `f4_evaluation_latency_seconds` | Histogram | — | Total per-analysis |
| `f4_criterion_latency_seconds` | Histogram | `criterion_id` | Per-criterion |
| `f4_criterion_outcome_total` | Counter | `criterion_id`, `outcome` (`evaluated`/`unverifiable`/`failed`) | Funnel |
| `f4_override_total` | Counter | `override_code` | Frequency |
| `f4_band_total` | Counter | `band` | Score distribution |
| `f4_findings_count` | Histogram | — | Findings per analysis |
| `f4_cost_cents_total` | Counter | — | LLM cost |
| `f4_legal_basis_empty_total` | Counter | `tag` (`market_based`/`unverifiable_legal`) | Coverage |

---

## Error Codes

| Code | Description |
|---|---|
| `RUBRIC_VERSION_NOT_ACTIVE` | No active rubric version found |
| `ECONOMIC_BARRIER_TIMEOUT` | F5 hasn't written `economic_summary` after 60 s |
| `TIMEOUT_EXCEEDED` | F4 total wall time exceeded 5 min |
| `LLM_AUTH_FAILED` | OpenRouter 401 |
| `LLM_TRANSIENT_FAILURE` | After retries |
| `PERSIST_FAILED` | Database write failure |

---

## Configuration matrix

| Variable | Default | Purpose |
|---|---|---|
| `LLM_RUBRIC_MODEL` | `anthropic/claude-sonnet-4` | LLM for criterion + summary |
| `LLM_RUBRIC_TIMEOUT_PER_CRITERION_SECONDS` | 30 | Per call |
| `LLM_RUBRIC_CONCURRENCY` | 8 | Parallel calls |
| `LLM_RUBRIC_TEMPERATURE` | 0.1 | — |
| `LLM_RUBRIC_MAX_RETRIES_PER_CRITERION` | 1 | After failure |
| `F4_ECONOMIC_BARRIER_TIMEOUT_SECONDS` | 60 | Wait for F5 |
| `F4_HARD_TIMEOUT_SECONDS` | 300 | Total budget |
| `RUBRIC_STREAM_GROUP` | `rubric` | Consumer group |
| `RUBRIC_STREAM_NAME_IN` | `classification.to_rubric_and_economics` | F2→F4 |

---

**End of document.**
