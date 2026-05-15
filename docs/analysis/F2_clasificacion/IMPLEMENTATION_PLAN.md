# Implementation Plan — F2: Contract Classification & Structured Extraction

> Generated: 2026-05-15
> Stack: **Django 5.2 LTS + DRF + Celery + Redis + Postgres 15**. See `../_shared/GLOBAL_ASSUMPTIONS.md`.
> Module: `classification/` at the project root.
> Depends on: F1 (extracted text), F8 (schema).
> Blocks: F4 (rubric), F5 (economic).

---

## Directory Structure

```
classification/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py            # ClassificationJob, ClassificationResult, LeasingIndicators, ElementsDetected, EconomicFieldsRaw, IndicatorDetection, ExtractedNumeric/ExtractedEnum
│   ├── enums.py               # ContractType, ClassificationStep, ClassificationJobStatus, ReclassificationSeverity, PaymentPeriodicity, InterestCalculationBase
│   └── exceptions.py          # ClassificationDomainException + subclasses
├── application/
│   ├── __init__.py
│   ├── commands.py            # ClassifyContract, UpdateAnalysisClassification, FindOrCreateProject, CreateClassificationJob, CompleteClassificationJob
│   ├── queries.py             # GetActiveRubricVersion, GetProjectByNormalizedName
│   ├── contracts/
│   │   ├── __init__.py
│   │   └── messages.py        # ClassificationDone envelope
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── classification_handlers.py
│   │   ├── project_handlers.py
│   │   └── classification_job_handlers.py
│   └── services/
│       ├── __init__.py
│       ├── classification_service.py
│       └── project_name_normalizer.py
└── infrastructure/
    ├── __init__.py
    ├── django/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py                       # ClassificationConfig
    │   ├── models.py                     # ClassificationJobModel + re-export of ContractAnalysisModel, ProjectModel
    │   ├── repositories.py               # ContractAnalysisRepository, ProjectRepository, ClassificationJobRepository
    │   ├── serializers.py                # InternalClassifyRequest, InternalClassifyResponse
    │   ├── views.py                      # InternalClassifyView
    │   ├── urls.py
    │   └── migrations/
    │       └── 0001_initial.py           # classification_job table only
    ├── celery/
    │   ├── __init__.py
    │   └── classification_tasks.py       # @shared_task process_classification, retry_classification
    ├── llm/
    │   ├── __init__.py
    │   ├── prompts.py                    # Verbatim PRD §8.1/§8.2/§8.3/§8.4/§8.5 templates
    │   ├── parser.py                     # Strict JSON parser with recovery
    │   └── steps/
    │       ├── __init__.py
    │       ├── base.py                   # LlmStep Protocol
    │       ├── classify_and_extract.py
    │       ├── validate.py
    │       ├── detect_leasing.py
    │       └── extract_economic.py
    └── redis/
        ├── __init__.py
        ├── stream_consumer.py            # ClassificationConsumer daemon (XREADGROUP)
        └── stream_publisher.py           # ClassificationStreamPublisher → classification.to_rubric_and_economics
```

---

## App Configuration

```python
# classification/infrastructure/django/apps.py
from django.apps import AppConfig

class ClassificationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "classification.infrastructure.django"
    label = "classification"
    verbose_name = "Casa Segura — Classification"

    def ready(self) -> None:
        pass
```

`INSTALLED_APPS` includes `"classification.infrastructure.django"`. `MIGRATION_MODULES` includes `"classification": "classification.infrastructure.django.migrations"`. URL include in `config/urls.py`:

```python
url_patterns_v1 = [
    # ...
    path("internal/classify/", include("classification.infrastructure.django.urls")),
]
```

---

## Domain Entities (Pydantic)

```python
# classification/domain/entities.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from classification.domain.enums import (
    ContractType, ClassificationStep, ClassificationJobStatus,
    ReclassificationSeverity, PaymentPeriodicity, InterestCalculationBase,
)


class IndicatorDetection(BaseModel):
    detected: bool
    evidence: str | None = None  # verbatim quote, max 500 chars


class LeasingIndicators(BaseModel):
    mandatory_term: IndicatorDetection
    predefined_purchase_option: IndicatorDetection
    ownership_retained: IndicatorDetection
    taxes_to_buyer: IndicatorDetection
    risks_to_buyer: IndicatorDetection
    payments_as_rent: IndicatorDetection
    indicators_count: int = Field(ge=0, le=6)
    should_reclassify: bool
    reclassification_severity: ReclassificationSeverity


class ElementsDetected(BaseModel):
    warranty_clause: bool = False
    warranty_exemption_clause: bool = False
    bien_de_familia_mention: bool = False
    fsv_mention: bool = False
    urbanism_permit_mention: bool = False
    promise_to_sell: bool = False
    public_deed: bool = False
    arbitration_clause: bool = False
    blank_signature: bool = False
    rights_waiver: bool = False
    unilateral_modification: bool = False
    late_interest_on_total_balance: bool = False


class ExtractedNumeric(BaseModel):
    value: float | None = None
    currency: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_snippet: str | None = None
    extraction_note: str | None = None
    extraction_status: str = "ok"  # ok | not_present | ambiguous | invalid


class ExtractedEnum(BaseModel):
    value: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_snippet: str | None = None
    extraction_status: str = "ok"


class EconomicFieldsRaw(BaseModel):
    price_cash: ExtractedNumeric | None = None
    down_payment: ExtractedNumeric | None = None
    down_payment_pct: ExtractedNumeric | None = None
    financed_amount: ExtractedNumeric | None = None
    term_months: ExtractedNumeric | None = None
    annual_rate_pct: ExtractedNumeric | None = None
    monthly_rate_pct: ExtractedNumeric | None = None
    monthly_payment: ExtractedNumeric | None = None
    payment_periodicity: ExtractedEnum | None = None
    interest_calculation_base: ExtractedEnum | None = None


class ClassificationResult(BaseModel):
    contract_type: ContractType
    contract_type_declared: ContractType | None = None
    contract_type_reclassified: bool = False
    reclassification_reason: str | None = None
    reclassification_indicators: LeasingIndicators | None = None
    classification_confidence: float = Field(ge=0.0, le=1.0)
    classification_attempts: int = 1
    project_name_canonical: str | None = None
    project_name_normalized: str
    elements_detected: ElementsDetected
    economic_fields_raw: EconomicFieldsRaw | None = None


class ClassificationJob(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    submission_id: UUID
    analysis_id: UUID | None = None
    step: ClassificationStep
    attempt_number: int = 1
    model_used: str
    started_at: datetime
    completed_at: datetime | None = None
    status: ClassificationJobStatus = ClassificationJobStatus.RUNNING
    tokens_consumed: int | None = None
    cost_estimate_cents: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    expires_at: datetime
```

## Enumerations

```python
# classification/domain/enums.py
from django.db import models


class ContractType(models.TextChoices):
    CVC = "CVC", "Cash purchase"
    CVP = "CVP", "Installment purchase"
    ARV = "ARV", "Residential lease"
    ARC = "ARC", "Commercial lease (small)"
    APV = "APV", "Lease with promise to sell"
    LEA = "LEA", "Financial leasing (real estate)"
    IVU = "IVU", "IVU institutional contract"
    FSV = "FSV", "FSV-financed purchase or loan"
    NOT_CLASSIFIABLE = "NOT_CLASSIFIABLE", "Not classifiable"


class ClassificationStep(models.TextChoices):
    CLASSIFICATION = "classification", "Classification"
    LEASING_DETECTION = "leasing_detection", "Leasing detection"
    ECONOMIC_EXTRACTION = "economic_extraction", "Economic extraction"
    ELEMENTS_DETECTION = "elements_detection", "Elements detection"


class ClassificationJobStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    TIMEOUT = "timeout", "Timeout"


class ReclassificationSeverity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class PaymentPeriodicity(models.TextChoices):
    MONTHLY = "monthly"
    BIWEEKLY = "biweekly"
    WEEKLY = "weekly"
    OTHER = "other"


class InterestCalculationBase(models.TextChoices):
    OUTSTANDING_PRINCIPAL = "outstanding_principal"
    TOTAL_BALANCE = "total_balance"
    UNSPECIFIED = "unspecified"
```

## Commands and Queries

```python
# classification/application/commands.py
from uuid import UUID
from pydantic import BaseModel
from classification.domain.entities import ClassificationJob, ClassificationResult
from classification.domain.enums import ClassificationJobStatus


class ClassifyContract(BaseModel):
    submission_id: UUID
    analysis_id: UUID
    extracted_text: str  # in-memory


class UpdateAnalysisClassification(BaseModel):
    analysis_id: UUID
    result: ClassificationResult


class FindOrCreateProject(BaseModel):
    canonical_name: str
    normalized_name: str
    placeholder: bool = False
    metadata_extra: dict = {}


class CreateClassificationJob(BaseModel):
    job: ClassificationJob


class CompleteClassificationJob(BaseModel):
    job_id: UUID
    status: ClassificationJobStatus
    tokens_consumed: int | None = None
    cost_estimate_cents: int | None = None
    error_code: str | None = None
    error_message: str | None = None
```

```python
# classification/application/queries.py
from shared.domain.entities.cqrs import BaseGetAttributes, Query


class GetActiveRubricVersion(BaseGetAttributes, Query):
    pass


class GetProjectByNormalizedName(BaseGetAttributes, Query):
    normalized_name: str
```

```python
# classification/application/contracts/messages.py
from uuid import UUID
from pydantic import BaseModel
from classification.domain.entities import ElementsDetected, EconomicFieldsRaw
from classification.domain.enums import ContractType


class ClassificationOutcome(BaseModel):
    contract_type: ContractType
    contract_type_declared: ContractType | None
    contract_type_reclassified: bool
    reclassification_reason: str | None
    classification_confidence: float


class ClassificationDone(BaseModel):
    submission_id: UUID
    analysis_id: UUID
    project_id: UUID
    extracted_text: str  # in-memory
    classification: ClassificationOutcome
    economic_fields_raw: EconomicFieldsRaw | None
    elements_detected: ElementsDetected
```

## New Dependencies

| Package | Version | Reason |
|---|---|---|
| (reuses everything F1 already added) | | |
| `unidecode` | ≥ 1.3 | Accent stripping for project name normalization |
| `pyyaml` | ≥ 6.0 | Already present (used elsewhere) — used to load prompt templates from `prompts.yaml` if we externalize them |

---

## Story: US-01 — Classify contract

### Acceptance Criteria

- LLM call with PRD §8.1/§8.2, validation §8.3 when needed
- Output validated against Pydantic; malformed → retry; double fail → `failed_classification`
- Persisted columns: `contract_type`, `contract_type_declared`, `contract_type_reclassified`, `reclassification_reason`, `reclassification_indicators`, `classification_confidence`, `classification_attempts`, `elements_detected`

### Dependencies

- F1 publishing to `ingestion.to_classification`
- F8 schema present
- `OpenRouterClient` (shared with F1)

### Files to Create

`classification_service.py`, `classify_and_extract.py`, `validate.py`, `parser.py`, repositories, Celery task, consumer daemon, internal endpoint.

### API Endpoints (internal only)

| Method | URL | Auth | Request | Response |
|---|---|---|---|---|
| POST | `/v1/internal/classify` | `HasInternalAuthHeader` | `{text, force_type?, skip_leasing_check?}` | 200 `{result: ClassificationResult, tokens_consumed_total, cost_estimate_cents}` |

---

## Story: US-02 — Project name extraction & matching

### Acceptance Criteria

- `project_name_canonical` extracted by the §8.1 prompt
- Normalized via `ProjectNameNormalizer`
- Upsert by `normalized_name`; placeholder when missing
- Report always carries the note "el nombre se extrajo del contrato; no se verificó"

### Files to Create

`project_name_normalizer.py`, `project_handlers.py`, `ProjectRepository.upsert`.

### Reference Code

```python
# classification/application/services/project_name_normalizer.py
import re
from unidecode import unidecode

GENERIC_WORDS = {"proyecto", "residencial", "condominio", "urbanizacion", "lotificacion", "complejo", "parque"}

class ProjectNameNormalizer:
    """Normalize a project canonical name to a matching slug.

    Rules: lowercase, strip accents, drop generic words at start/end positions,
    collapse multiple spaces to one, drop chars outside [a-z0-9 -]. If result
    has fewer than 3 chars, returns empty string (caller must use placeholder).
    """
    _NON_ALNUM = re.compile(r"[^a-z0-9 -]")
    _MULTI_SPACE = re.compile(r"\s+")

    def normalize(self, canonical: str | None) -> str:
        if not canonical:
            return ""
        s = unidecode(canonical).lower()
        s = self._NON_ALNUM.sub(" ", s)
        s = self._MULTI_SPACE.sub(" ", s).strip()
        tokens = s.split(" ")
        # drop generic words at start
        while tokens and tokens[0] in GENERIC_WORDS:
            tokens.pop(0)
        # drop generic words at end
        while tokens and tokens[-1] in GENERIC_WORDS:
            tokens.pop()
        result = " ".join(tokens)
        return result if len(result) >= 3 else ""
```

### Test Cases

- [ ] "Residencial Las Palmeras" → `las palmeras`
- [ ] "PROYECTO URBANO CUMBRES DEL VOLCÁN" → `urbano cumbres del volcan`
- [ ] "CONDOMINIO ARRECIFE 2" → `arrecife 2`
- [ ] "Lotificación El Roble" → `el roble`
- [ ] Empty / null → empty string → placeholder
- [ ] "Residencial" alone → empty → placeholder
- [ ] "Res. Cumbres" → `res cumbres`
- [ ] Two contracts with "El Roble" and "Residencial El Roble" → both normalize to `el roble`; same Project

---

## Story: US-03 — Leasing reclassification

### Acceptance Criteria

- Trigger on type ∈ {CVC, CVP, APV}
- PRD §8.4 prompt with idempotency key
- Reclassify when `indicators_count ≥ LEASING_RECLASSIFICATION_THRESHOLD` (default 4)
- Record `reclassification_indicators` as JSONB for F4

### Test Cases

- [ ] 5/6 indicators on CVP → type LEA, reason describes the 5 detected
- [ ] 3/6 indicators on CVP → no reclassification, but JSONB stored
- [ ] 0/6 indicators on CVP → reclassification_indicators = NULL
- [ ] Original type CVP, declared = CVP, post LEA, declared still CVP
- [ ] LLM returns malformed indicator JSON → recovery; if fails twice → failed_classification

---

## Story: US-04 — Economic field extraction

### Acceptance Criteria

- Trigger on type ∈ {CVP, APV, LEA, FSV, ARV}
- PRD §8.5 prompt
- Output `EconomicFieldsRaw` validated against Pydantic
- Auto-derive `annual_rate_pct` from `monthly_rate_pct` when only monthly given
- Pass to F4/F5 via `ClassificationDone` envelope — NOT persisted by F2

### Test Cases

- [ ] All fields present → all populated, confidence > 0.5
- [ ] Only monthly rate → annual derived `(1+monthly)^12 - 1`, note set
- [ ] `interest_calculation_base = total_balance` → flagged for F4
- [ ] Field out of range (annual 1.5) → extraction_status=invalid
- [ ] Currency = SVC → no conversion (F5 owns conversion)

---

## Story: US-05 — Element detection (within classification call)

### Acceptance Criteria

- `elements_detected` is part of the §8.1 response payload
- 12 boolean flags persisted as JSONB on `contract_analysis.elements_detected`

### Test Cases

- [ ] Contract with arbitration clause → `arbitration_clause=true`
- [ ] Contract with blank-signature clause → `blank_signature=true`
- [ ] Mute contract → all flags `false`

---

## Story: US-06 — Handle NOT_CLASSIFIABLE

### Acceptance Criteria

- Mark `contract_type=NOT_CLASSIFIABLE`
- UPDATE `contract_submission.processing_status='rejected_type'`
- Notify user via the channel they chose
- Do not publish to F4/F5

### Test Cases

- [ ] LLM returns confidence 0.40 → rejected
- [ ] LLM returns out-of-enum type → rejected
- [ ] Two attempts disagree → rejected
- [ ] Status endpoint returns `error.message` translated

---

## Part 2 — Staged Execution Plan

### Codebase Alignment Rules

- Same as F1 + this:
- `ClassificationService` is a plain class with repositories and `OpenRouterClient` injected via `__init__(*, ...=...)`
- `ClassificationJobModel` is owned by F2 (its migration is in `classification/infrastructure/django/migrations/`)
- `ContractAnalysisModel`, `ProjectModel` are re-imports from `platform.infrastructure.django.models`
- Celery tasks: `@shared_task(name="classification.<name>")`
- LLM prompts kept in Spanish in `classification/infrastructure/llm/prompts.py` (one constant per prompt) — verbatim from PRD §8

### Stage Overview

| # | Stage | Deliverable | Depends On |
|---|---|---|---|
| 1 | Domain entities + enums + exceptions | Pydantic + TextChoices | — |
| 2 | Commands, queries, envelope | CQRS contracts | Stage 1 |
| 3 | Handlers | Plain functions | Stage 2 |
| 4 | Service classes | `ClassificationService`, `ProjectNameNormalizer` | Stage 3 |
| 5 | LLM steps + parser | `prompts.py`, `parser.py`, `steps/*.py` | Stage 4 |
| 6 | Django model + migration | `ClassificationJobModel` migration | F8 schema |
| 7 | Repositories | `ClassificationJobRepository`, `ProjectRepository.upsert`, `ContractAnalysisRepository.update_classification` | Stages 4+6 |
| 8 | Internal API | `InternalClassifyView` + serializers + URLs | Stage 7 |
| 9 | Celery task | `process_classification` shared_task | Stages 7+8 |
| 10 | Stream consumer daemon | `ClassificationConsumer` and management command | Stage 9 |
| 11 | Tests | Unit + integration with `respx`-mocked LLM | All |
| 12 | Observability | Prometheus metrics | Stage 10 |
| 13 | Documentation | `classification/README.md` | All |

### Stage 1: Domain entities + enums + exceptions

#### Deliverables

- [ ] `classification/domain/entities.py`
- [ ] `classification/domain/enums.py`
- [ ] `classification/domain/exceptions.py` — subclasses of `DomainException`

#### Reference Code

```python
# classification/domain/exceptions.py
from common.domain.exceptions.core import DomainException

class ClassificationDomainException(DomainException):
    """Base for F2 errors."""

class ClassificationNotClassifiable(ClassificationDomainException):
    def __init__(self, reason: str) -> None:
        super().__init__(
            message="No pudimos clasificar tu documento como un contrato inmobiliario cubierto por Casa Segura.",
            code="TYPE_NOT_SUPPORTED",
            status=422,
            extra={"reason": reason},
        )

class ClassificationLlmFailed(ClassificationDomainException):
    def __init__(self, sub_code: str, message: str) -> None:
        super().__init__(message=message, code=f"LLM_{sub_code}", status=500)

class ClassificationParseError(ClassificationLlmFailed):
    def __init__(self, attempts: int) -> None:
        super().__init__(sub_code="PARSE_FAILED", message=f"LLM JSON parse failed after {attempts} attempts")
```

### Stage 5: LLM steps + parser

`classification/infrastructure/llm/prompts.py` holds verbatim Spanish prompts from PRD §8.1/§8.2/§8.3/§8.4/§8.5 as Python multiline strings with `{{placeholder}}` markers; substitution uses `string.Template`-style replacement.

`classification/infrastructure/llm/parser.py` provides:

```python
class JsonResponseParser:
    def parse(self, raw: str, target: type[BaseModel]) -> BaseModel:
        """Strip ``` fences, extract balanced { ... }, validate with Pydantic."""
```

`classification/infrastructure/llm/steps/base.py`:

```python
class LlmStep(Protocol):
    name: ClassificationStep
    response_model: type[BaseModel]

    def build_prompt(self, *, extracted_text: str, ctx: dict) -> list[dict]: ...

    async def run(self, *, extracted_text: str, ctx: dict, idempotency_key: str) -> BaseModel: ...
```

Each concrete step encapsulates one prompt + one response model + one idempotency-key suffix.

### Stage 6: Django model + migration

```python
# classification/infrastructure/django/models.py
import uuid
from django.db import models
from classification.domain.enums import ClassificationStep, ClassificationJobStatus

# Re-export for code locality
from platform.infrastructure.django.models import ContractAnalysisModel, ProjectModel  # noqa: F401


class ClassificationJobModel(models.Model):
    """Per-step observability for the LLM calls F2 issues. Transient."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Internal identifier.")
    submission_id = models.UUIDField(db_index=True, help_text="Owning submission (FK soft-ref to contract_submission).")
    analysis_id = models.UUIDField(null=True, blank=True, db_index=True, help_text="Owning analysis once known.")
    step = models.CharField(max_length=32, choices=ClassificationStep.choices, help_text="Which F2 step this job represents.")
    attempt_number = models.IntegerField(default=1, help_text="Retry number within the step (1 or 2).")
    model_used = models.CharField(max_length=128, help_text="OpenRouter model identifier.")
    started_at = models.DateTimeField(auto_now_add=True, help_text="Start time.")
    completed_at = models.DateTimeField(null=True, blank=True, help_text="End time.")
    status = models.CharField(max_length=16, choices=ClassificationJobStatus.choices, default=ClassificationJobStatus.RUNNING, help_text="Terminal state.")
    tokens_consumed = models.IntegerField(null=True, blank=True, help_text="LLM tokens billed for this step.")
    cost_estimate_cents = models.IntegerField(null=True, blank=True, help_text="Estimated USD cents.")
    error_code = models.CharField(max_length=64, null=True, blank=True, help_text="Normalized failure code.")
    error_message = models.TextField(null=True, blank=True, help_text="Operator-facing failure detail.")
    expires_at = models.DateTimeField(db_index=True, help_text="Cleanup trigger (F8 cron).")

    class Meta:
        db_table = "classification_job"
        indexes = [
            models.Index(fields=["submission_id"], name="idx_clsj_submission"),
            models.Index(fields=["analysis_id"], name="idx_clsj_analysis"),
            models.Index(fields=["expires_at"], name="idx_clsj_expires"),
            models.Index(fields=["step", "status"], name="idx_clsj_step_status"),
        ]

    def __str__(self) -> str:
        return f"ClassificationJob {self.id} ({self.step}, {self.status})"
```

Migration `0001_initial.py` creates only `classification_job`. The transient submission and analysis tables are F8-owned.

### Stage 9: Celery task

```python
# classification/infrastructure/celery/classification_tasks.py
from celery import shared_task
from classification.application.services.classification_service import ClassificationService


@shared_task(name="classification.process_classification", bind=True, max_retries=1)
def process_classification(self, envelope_json: str) -> None:
    """Consume an ExtractionDone envelope and run the F2 chain.
    Idempotent: re-running with the same submission_id/analysis_id is safe."""
    service = ClassificationService(...)  # built via Django settings + repositories factories
    service.classify_from_envelope_json(envelope_json)
```

### Stage 10: Stream consumer daemon

Implemented as a Django management command:

```python
# classification/infrastructure/redis/stream_consumer.py
import redis
from django.core.management.base import BaseCommand

STREAM = "ingestion.to_classification"
GROUP = "classification"

class Command(BaseCommand):
    """Daemon: python manage.py run_classification_consumer"""
    def handle(self, *args, **opts):
        r = redis.Redis.from_url(settings.REDIS_URL)
        # ensure group exists
        try:
            r.xgroup_create(STREAM, GROUP, id="$", mkstream=True)
        except redis.ResponseError:
            pass
        while True:
            msgs = r.xreadgroup(GROUP, "consumer-1", {STREAM: ">"}, count=10, block=5000)
            for _stream, entries in msgs or []:
                for msg_id, fields in entries:
                    try:
                        from classification.infrastructure.celery.classification_tasks import process_classification
                        process_classification.delay(fields[b"envelope"].decode())
                        r.xack(STREAM, GROUP, msg_id)
                    except Exception:
                        # do not ack; message will be re-read after PEL timeout
                        ...
```

The consumer runs as its own process. In Docker Compose: a service `classification-consumer` running the management command.

---

## Error Codes (canonical list owned by F2)

| Code | HTTP | Description |
|---|---|---|
| `TYPE_NOT_SUPPORTED` | 422 | Contract type is not one of the eight covered |
| `LLM_AUTH_FAILED` | — | Surface as 500 internal |
| `LLM_TRANSIENT_FAILURE` | — | Surface as 500 after retries |
| `LLM_PARSE_FAILED` | — | LLM JSON unparseable after recovery |
| `LLM_CIRCUIT_OPEN` | — | Circuit breaker open |
| `CLASSIFICATION_TIMEOUT` | — | Single LLM call exceeded 30 s |
| `CLASSIFICATION_ATTEMPTS_DISAGREE` | — | Two attempts produced different types |

---

## Configuration matrix (all F2 env vars)

| Variable | Default | Purpose |
|---|---|---|
| `LLM_CLASSIFICATION_MODEL` | `anthropic/claude-sonnet-4` | OpenRouter model |
| `LLM_CLASSIFICATION_FALLBACK_MODEL` | (unset) | Optional alt model on first-model permanent failure |
| `LLM_CLASSIFICATION_TEMPERATURE` | 0.1 | — |
| `LLM_TIMEOUT_PER_CALL_SECONDS` | 30 | Per LLM call |
| `LLM_CLASSIFICATION_CONFIDENCE_HIGH` | 0.85 | Accept directly above |
| `LLM_CLASSIFICATION_CONFIDENCE_LOW` | 0.65 | Reject below |
| `LEASING_RECLASSIFICATION_THRESHOLD` | 4 | Indicator count to reclassify |
| `CLASSIFICATION_STREAM_GROUP` | `classification` | Redis Streams consumer group |
| `CLASSIFICATION_STREAM_NAME_IN` | `ingestion.to_classification` | F1→F2 stream |
| `CLASSIFICATION_STREAM_NAME_OUT` | `classification.to_rubric_and_economics` | F2→F4/F5 stream |
| `CLASSIFICATION_JOB_TTL_HOURS` | 24 | Cleanup |
| `OPENROUTER_API_KEY` | — | (shared with F1) |
| `OPENROUTER_*_CB_*` | (shared) | Circuit breaker config |

---

**End of document.**
