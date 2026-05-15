# Implementation Plan — F1: Ingestion & Text Extraction Pipeline

> Generated: 2026-05-15
> Stack: **Django 5.2 LTS + DRF 3.15+ + Celery 5.4 + Redis + Postgres 15 + pgvector**. See `../_shared/GLOBAL_ASSUMPTIONS.md` §1 for rationale and the full convention map.
> Module: `ingestion/` at the project root.

---

## Directory Structure

```
ingestion/
├── __init__.py
├── domain/
│   ├── __init__.py
│   ├── entities.py            # Pydantic: ContractSubmission, OcrJob, ExtractedDocument
│   ├── enums.py               # ProcessingStatus, ExtractionStrategy, OcrJobStatus, SubmissionSource, DisclaimerAcceptanceMethod
│   └── exceptions.py          # IngestionDomainException + subclasses
├── application/
│   ├── __init__.py
│   ├── commands.py            # CreateSubmission, UpdateSubmissionStatus, CreateOcrJob, CompleteOcrJob, MarkSubmissionExpired
│   ├── queries.py             # GetSubmissionByHash, GetSubmissionByPublicShortId, GetSubmissionById, FilterSubmissions
│   ├── contracts/
│   │   ├── __init__.py
│   │   └── messages.py        # ExtractionDone envelope (Pydantic)
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── submission_handlers.py
│   │   └── ocr_handlers.py
│   └── services/
│       ├── __init__.py
│       ├── ingestion_service.py        # Main orchestration class
│       ├── extraction_orchestrator.py  # Strategy routing
│       ├── whatsapp_session.py
│       ├── short_id_generator.py
│       └── disclaimer_recognition.py
└── infrastructure/
    ├── __init__.py
    ├── django/
    │   ├── __init__.py
    │   ├── admin.py
    │   ├── apps.py                       # IngestionConfig
    │   ├── models.py                     # ContractSubmissionModel, OcrJobModel
    │   ├── repositories.py               # ContractSubmissionRepository, OcrJobRepository, AnalysisStubRepository, AnalysisLookupRepository
    │   ├── serializers.py                # SubmitRequestSerializer, SubmissionAcceptedSerializer, SubmissionStatusSerializer, ZavuWebhookPayloadSerializer
    │   ├── views.py                      # SubmissionViewSet, ZavuWebhookView, InternalRetryView
    │   ├── urls.py                       # Module URL patterns
    │   ├── throttles.py                  # BurstSubmitThrottle, WhatsAppSubmitThrottle
    │   ├── permissions.py                # ValidatesZavuSignature (lives in shared but referenced here)
    │   ├── exception_handler.py          # DRF custom exception handler mapping DomainException -> JSON
    │   ├── signals.py                    # (none for F1 in MVP)
    │   └── migrations/
    │       └── __init__.py               # See F8 for the actual table DDL; F1 only adds its own per-module migrations if needed
    ├── celery/
    │   ├── __init__.py
    │   └── ingestion_tasks.py            # @shared_task: process_submission, retry_submission, mark_stuck_submissions
    ├── ocr/
    │   ├── __init__.py
    │   ├── base.py                       # ExtractionStrategy Protocol, JobResult, PageResult, PageList
    │   ├── pypdf_extractor.py
    │   ├── vision_llm_extractor.py
    │   ├── tesseract_extractor.py
    │   └── language_detector.py
    ├── llm/
    │   ├── __init__.py
    │   ├── openrouter_client.py          # Circuit-breaker-wrapped client (sync httpx in Celery tasks)
    │   └── pricing.py                    # Per-model token pricing table
    ├── external/
    │   ├── __init__.py
    │   └── zavu_client.py                # Signature verification, media download, send
    └── redis/
        ├── __init__.py
        ├── session_store.py              # WhatsApp sessions
        ├── stream_publisher.py           # Publishes ExtractionDone to ingestion.to_classification
        ├── stream_consumer.py            # Background process consuming ingestion.from_submit
        └── keyspace_listener.py          # Subscribes to __keyevent@0__:expired for whatsapp_session
```

---

## App Configuration

**`ingestion/infrastructure/django/apps.py`**

```python
from django.apps import AppConfig

class IngestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ingestion.infrastructure.django"
    label = "ingestion"
    verbose_name = "Casa Segura — Ingestion & OCR"

    def ready(self) -> None:
        # No signals in F1 MVP; placeholder for future
        pass
```

In `config/settings/base.py`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",         # required by Django, even though Casa Segura has no end users; admin uses it
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "softdelete",                  # for SoftDeleteObject (not used by F1 transient tables, used elsewhere)
    "platform.infrastructure.django",      # F8 — schema and Project + ContractAnalysis
    "ingestion.infrastructure.django",     # F1
    "classification.infrastructure.django",# F2
    "corpus.infrastructure.django",        # F3
    "rubric.infrastructure.django",        # F4
    "economics.infrastructure.django",     # F5
    "reports.infrastructure.django",       # F6
    "delivery.infrastructure.django",      # F7
]

MIGRATION_MODULES = {
    "platform": "platform.infrastructure.django.migrations",
    "ingestion": "ingestion.infrastructure.django.migrations",
    "classification": "classification.infrastructure.django.migrations",
    "corpus": "corpus.infrastructure.django.migrations",
    "rubric": "rubric.infrastructure.django.migrations",
    "economics": "economics.infrastructure.django.migrations",
    "reports": "reports.infrastructure.django.migrations",
    "delivery": "delivery.infrastructure.django.migrations",
}
```

In `config/urls.py`:

```python
url_patterns_v1 = [
    path("contracts/", include("ingestion.infrastructure.django.urls")),
    path("zavu/", include("ingestion.infrastructure.django.urls_zavu")),  # webhook router
    # ... other modules
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("v1/", include(url_patterns_v1)),
    path("metrics", include("django_prometheus.urls")),
    path("v1/openapi.json", SpectacularAPIView.as_view(), name="schema"),
]
```

---

## Domain Entities (Pydantic)

```python
# ingestion/domain/entities.py
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from ingestion.domain.enums import (
    ProcessingStatus, ExtractionStrategy, OcrJobStatus,
    SubmissionSource, DisclaimerAcceptanceMethod,
)


class ContractSubmission(BaseModel):
    """A single user upload act; transient (24 h)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    submission_hash: str
    public_short_id: str
    file_count: int = Field(ge=1, le=50)
    total_size_bytes: int
    total_pages: int | None = None
    file_formats: list[str]
    source: SubmissionSource
    source_metadata: dict[str, str] = Field(default_factory=dict)
    processing_status: ProcessingStatus = ProcessingStatus.RECEIVED
    extraction_strategy_attempted: ExtractionStrategy | None = None
    extraction_strategy_successful: ExtractionStrategy | None = None
    extracted_text_token_count: int | None = None
    extracted_text_language: str | None = None
    extracted_text_language_confidence: float | None = None
    error_code: str | None = None
    error_reason: str | None = None
    analysis_id: UUID | None = None
    disclaimer_accepted_at: datetime
    disclaimer_accepted_via: DisclaimerAcceptanceMethod
    received_at: datetime
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    expires_at: datetime


class OcrJob(BaseModel):
    """One observable run of one extraction strategy; transient."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    submission_id: UUID
    strategy: ExtractionStrategy
    attempt_number: int = 1
    model_used: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    status: OcrJobStatus
    pages_processed: int | None = None
    pages_failed: int | None = None
    tokens_consumed: int | None = None
    cost_estimate_cents: int | None = None
    average_confidence: float | None = None
    error_code: str | None = None
    error_message: str | None = None
    expires_at: datetime


class ExtractedDocument(BaseModel):
    """In-memory result passed in the F1→F2 envelope. NEVER persisted to Postgres."""
    text: str
    strategy_used: ExtractionStrategy
    pages_processed: int
    pages_failed: int
    tokens_consumed: int
    cost_estimate_cents: int
    language_detected: str
    language_confidence: float
```

## Enumerations

```python
# ingestion/domain/enums.py
from enum import StrEnum
from django.db import models


class ProcessingStatus(models.TextChoices):
    RECEIVED = "received", "Received"
    EXTRACTING = "extracting", "Extracting"
    EXTRACTED = "extracted", "Extracted"
    CLASSIFYING = "classifying", "Classifying"
    ANALYZING = "analyzing", "Analyzing"
    COMPLETED = "completed", "Completed"
    FAILED_EXTRACTION = "failed_extraction", "Failed extraction"
    FAILED_CLASSIFICATION = "failed_classification", "Failed classification"
    FAILED_ANALYSIS = "failed_analysis", "Failed analysis"
    REJECTED_LANGUAGE = "rejected_language", "Rejected language"
    REJECTED_TYPE = "rejected_type", "Rejected type"
    REJECTED_SIZE = "rejected_size", "Rejected size"
    EXPIRED = "expired", "Expired"


class ExtractionStrategy(models.TextChoices):
    PYPDF = "pypdf", "pypdf"
    VISION_LLM = "vision_llm", "Vision LLM"
    TESSERACT = "tesseract", "Tesseract"


class OcrJobStatus(models.TextChoices):
    RUNNING = "running", "Running"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    TIMEOUT = "timeout", "Timeout"
    CANCELLED = "cancelled", "Cancelled"


class SubmissionSource(models.TextChoices):
    WEB = "web", "Web"
    WHATSAPP = "whatsapp", "WhatsApp"


class DisclaimerAcceptanceMethod(models.TextChoices):
    WEB_CHECKBOX = "web_checkbox", "Web checkbox"
    WHATSAPP_REPLY = "whatsapp_reply", "WhatsApp reply"
```

`TextChoices` is used because these enums power both the domain (Pydantic `Field(... choices=...)`) and the Django model `CharField(choices=...)`. Pydantic accepts the string values directly via `model_config = ConfigDict(use_enum_values=True)` on the entity if needed; we prefer keeping the enum on the Pydantic side via `from_attributes=True` and reading `model.processing_status` (a Django CharField value) directly.

## Commands and Queries

```python
# ingestion/application/commands.py
from uuid import UUID
from pydantic import BaseModel
from ingestion.domain.entities import ContractSubmission, OcrJob
from ingestion.domain.enums import ProcessingStatus, OcrJobStatus


class CreateSubmission(BaseModel):
    submission: ContractSubmission


class UpdateSubmissionStatus(BaseModel):
    submission_id: UUID
    new_status: ProcessingStatus
    extraction_strategy_attempted: str | None = None
    extraction_strategy_successful: str | None = None
    extracted_text_token_count: int | None = None
    extracted_text_language: str | None = None
    extracted_text_language_confidence: float | None = None
    error_code: str | None = None
    error_reason: str | None = None
    set_processing_started_at: bool = False
    set_processing_completed_at: bool = False


class CreateOcrJob(BaseModel):
    job: OcrJob


class CompleteOcrJob(BaseModel):
    job_id: UUID
    status: OcrJobStatus
    pages_processed: int | None = None
    pages_failed: int | None = None
    tokens_consumed: int | None = None
    cost_estimate_cents: int | None = None
    average_confidence: float | None = None
    error_code: str | None = None
    error_message: str | None = None
```

```python
# ingestion/application/queries.py
from uuid import UUID
from shared.domain.entities.cqrs import BaseFilterAttributes, BaseGetAttributes, Query


class GetSubmissionById(BaseGetAttributes, Query):
    pass


class GetSubmissionByPublicShortId(BaseGetAttributes, Query):
    pass


class GetSubmissionByHash(BaseGetAttributes, Query):
    pass


class FilterSubmissions(BaseFilterAttributes, Query):
    pass


class GetExistingAnalysisByHash(BaseGetAttributes, Query):
    submission_hash: str
    require_not_anonymized: bool = True
```

```python
# ingestion/application/contracts/messages.py
from uuid import UUID
from pydantic import BaseModel
from ingestion.domain.enums import ExtractionStrategy


class ExtractionMetadata(BaseModel):
    strategy_used: ExtractionStrategy
    pages_processed: int
    pages_failed: int
    tokens_consumed: int
    language_detected: str
    language_confidence: float


class ExtractionDone(BaseModel):
    """F1 → F2 Redis Streams envelope. Carries in-memory extracted_text."""
    submission_id: UUID
    analysis_id: UUID
    extracted_text: str
    extraction_metadata: ExtractionMetadata
```

## New Dependencies

| Package | Version | Reason |
|---|---|---|
| `Django` | 5.2.x (LTS) | HTTP framework |
| `djangorestframework` | ≥ 3.15 | REST views, serializers, throttling |
| `drf-spectacular` | ≥ 0.27 | OpenAPI schema |
| `django-prometheus` | ≥ 2.3 | `/metrics` endpoint |
| `django-environ` | ≥ 0.11 | Env loading |
| `django-softdelete` | latest | `SoftDeleteObject` (transient F1 tables do not soft-delete; required by other modules) |
| `django-celery-beat` | ≥ 2.6 | Periodic task DB scheduler |
| `pydantic` | ≥ 2.5 | Domain entities, commands, envelopes |
| `psycopg[binary]` | ≥ 3.1 | Postgres driver |
| `pgvector` | ≥ 0.3 | Vector support (used by F3, declared globally) |
| `redis` | ≥ 5.0 | Streams, sessions, broker for Celery |
| `celery[redis]` | ≥ 5.4 | Async tasks |
| `httpx` | ≥ 0.27 | Outgoing HTTP for OpenRouter and Zavu (sync, used inside Celery tasks) |
| `pypdf` | ≥ 4.0 | PDF native text extraction |
| `pdf2image` | ≥ 1.17 | PDF→JPEG rasterization (requires `poppler-utils` OS pkg in worker image) |
| `Pillow` | ≥ 10.2 | Image processing |
| `pillow-heif` | ≥ 0.16 | HEIC support (requires `libheif` OS pkg in worker image) |
| `pytesseract` | ≥ 0.3.10 | Tesseract bindings |
| `tiktoken` | ≥ 0.6 | Token counting (for cost auditing) |
| `langdetect` | ≥ 1.0.9 | Language detection (default) |
| `lingua-language-detector` | ≥ 2.0 | Alternative language detector |
| `structlog` | ≥ 24.0 | Structured logging |
| OS: `tesseract-ocr` + `tesseract-ocr-spa` | latest | Tesseract binary + Spanish pack (worker image only) |
| OS: `libheif1`, `libheif-dev` | latest | HEIC decoding (worker image only) |
| OS: `poppler-utils` | latest | `pdf2image` backend (worker image only) |

---

## Story: US-01 — User uploads the contract from the web

### Acceptance Criteria (from PRD)

- Upload via multipart with all validations from `PRD_F1` §3 US-01
- Disclaimer enforced server-side
- 201 response with `submission_id`, `public_short_id`, polling URL

### Dependencies

- F8 schema present: `contract_submission`, `ocr_job`, `contract_analysis`, `project` (with the seeded placeholder project `__unknown_pending__`)
- `shared/infrastructure/django/permissions.py` published (depends on the platform module)

### Files to Create

**`ingestion/infrastructure/django/views.py`** — *Submission viewset*
```python
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ingestion.application.services.ingestion_service import IngestionService
from ingestion.infrastructure.django import serializers
from ingestion.infrastructure.django.repositories import (
    ContractSubmissionRepository, OcrJobRepository,
    AnalysisStubRepository, AnalysisLookupRepository,
)
from ingestion.infrastructure.django.throttles import BurstSubmitThrottle
from ingestion.infrastructure.django.exception_handler import map_domain_exception


class SubmissionViewSet(viewsets.ViewSet):
    """Public endpoints for submitting contracts and polling status."""

    parser_classes = [MultiPartParser]
    permission_classes = [AllowAny]
    throttle_classes = [BurstSubmitThrottle]

    # Class-level service composition (per architecture conventions)
    ingestion_service = IngestionService(
        submission_repository=ContractSubmissionRepository(),
        ocr_repository=OcrJobRepository(),
        analysis_stub_repository=AnalysisStubRepository(),
        analysis_lookup_repository=AnalysisLookupRepository(),
    )

    @extend_schema(
        request=serializers.SubmitRequestSerializer,
        responses={
            201: serializers.SubmissionAcceptedSerializer,
            400: serializers.ErrorSerializer,
            409: serializers.DuplicateSerializer,
            413: serializers.ErrorSerializer,
            429: serializers.ErrorSerializer,
        },
        description="Submit one or more files representing a real estate contract.",
    )
    @action(detail=False, methods=["post"], url_path="submit")
    def submit(self, request):
        serializer = serializers.SubmitRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            accepted = self.ingestion_service.accept_web_submission(
                **serializer.validated_data,
                request_metadata=_extract_metadata(request),
            )
        except Exception as exc:
            return map_domain_exception(exc)
        return Response(
            serializers.SubmissionAcceptedSerializer(accepted).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses={200: serializers.SubmissionStatusSerializer, 404: OpenApiResponse(description="Not found")})
    @action(detail=True, methods=["get"], url_path="status")
    def status(self, request, pk: str):
        view = self.ingestion_service.get_status(submission_id_or_short_id=pk)
        if view is None:
            return Response({"error": {"code": "SUBMISSION_NOT_FOUND"}}, status=404)
        return Response(serializers.SubmissionStatusSerializer(view).data)
```

**`ingestion/infrastructure/django/serializers.py`**
```python
from rest_framework import serializers
from ingestion.domain.enums import ProcessingStatus

# Note: never use fields = '__all__'. Each serializer lists fields explicitly.

class SubmitRequestSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField(), min_length=1, max_length=50)
    disclaimer_accepted = serializers.BooleanField()
    delivery_channel = serializers.ChoiceField(choices=["email_pdf", "whatsapp_summary", "web_link"])
    delivery_target = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=320)
    force_strategy = serializers.ChoiceField(
        required=False, allow_null=True, choices=["pypdf", "vision_llm", "tesseract"],
    )

    def validate(self, attrs):
        if not attrs.get("disclaimer_accepted"):
            raise serializers.ValidationError({"disclaimer_accepted": "DISCLAIMER_REQUIRED"})
        channel = attrs["delivery_channel"]
        target = attrs.get("delivery_target")
        if channel in ("email_pdf", "whatsapp_summary") and not target:
            raise serializers.ValidationError({"delivery_target": "INVALID_DELIVERY_TARGET"})
        return attrs


class SubmissionAcceptedSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    public_short_id = serializers.CharField()
    analysis_id = serializers.UUIDField()
    processing_status = serializers.ChoiceField(choices=ProcessingStatus.choices)
    estimated_completion_seconds = serializers.IntegerField()
    status_url = serializers.CharField()


class DuplicateSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    public_short_id = serializers.CharField()
    processing_status = serializers.ChoiceField(choices=ProcessingStatus.choices)
    analysis_id = serializers.UUIDField()
    is_duplicate = serializers.BooleanField()
    message = serializers.CharField()


class SubmissionStatusSerializer(serializers.Serializer):
    submission_id = serializers.UUIDField()
    public_short_id = serializers.CharField()
    processing_status = serializers.ChoiceField(choices=ProcessingStatus.choices)
    progress = serializers.DictField(child=serializers.JSONField(), required=False)
    analysis_id = serializers.UUIDField(allow_null=True, required=False)
    report_url = serializers.CharField(required=False)
    error = serializers.DictField(child=serializers.JSONField(), required=False)
    started_at = serializers.DateTimeField(required=False)
    completed_at = serializers.DateTimeField(allow_null=True, required=False)


class ErrorSerializer(serializers.Serializer):
    error = serializers.DictField(child=serializers.JSONField())
```

**`ingestion/infrastructure/django/urls.py`**
```python
from rest_framework.routers import SimpleRouter
from ingestion.infrastructure.django import views

router = SimpleRouter()
router.register("", views.SubmissionViewSet, basename="contracts")

urlpatterns = router.urls
```

**`ingestion/infrastructure/django/throttles.py`**
```python
from rest_framework.throttling import SimpleRateThrottle


class BurstSubmitThrottle(SimpleRateThrottle):
    scope = "submit"
    rate = "5/hour"

    def get_cache_key(self, request, view):
        ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class WhatsAppSubmitThrottle(SimpleRateThrottle):
    """Applied at the service level inside the webhook handler, keyed by phone_hash."""
    scope = "wa_submit"
    rate = "3/hour"

    def get_cache_key_for(self, phone_hash: str) -> str:
        return self.cache_format % {"scope": self.scope, "ident": phone_hash}
```

**`ingestion/application/services/ingestion_service.py`** — Plain class per conventions, repositories injected via `__init__`:
```python
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from ingestion.application import commands, queries
from ingestion.application.handlers import submission_handlers, ocr_handlers
from ingestion.application.services.short_id_generator import ShortIdGenerator
from ingestion.domain.entities import ContractSubmission
from ingestion.domain.enums import ProcessingStatus, SubmissionSource, DisclaimerAcceptanceMethod
from ingestion.domain.exceptions import (
    DisclaimerRequiredError, DuplicateSubmissionError, FormatNotSupportedError,
)
from ingestion.infrastructure.redis.stream_publisher import SubmissionStreamPublisher
from shared.domain.entities import repositories as shared_repositories


class IngestionService:
    """Orchestration of web/WhatsApp submission acceptance."""

    def __init__(
        self,
        *,
        submission_repository: shared_repositories.BaseRepository,
        ocr_repository: shared_repositories.BaseRepository,
        analysis_stub_repository,
        analysis_lookup_repository,
        rubric_version_service=None,
        short_id_generator: ShortIdGenerator | None = None,
        stream_publisher: SubmissionStreamPublisher | None = None,
    ):
        self.submission_repository = submission_repository
        self.ocr_repository = ocr_repository
        self.analysis_stub_repository = analysis_stub_repository
        self.analysis_lookup_repository = analysis_lookup_repository
        self.rubric_version_service = rubric_version_service
        self.short_id_generator = short_id_generator or ShortIdGenerator()
        self.stream_publisher = stream_publisher or SubmissionStreamPublisher()

    def accept_web_submission(
        self,
        *,
        files: list,
        disclaimer_accepted: bool,
        delivery_channel: str,
        delivery_target: str | None,
        force_strategy: str | None,
        request_metadata: dict,
    ) -> "SubmissionAcceptedView":
        """Validate, hash, dedupe, stub-analysis, persist submission, enqueue for OCR."""
        if not disclaimer_accepted:
            raise DisclaimerRequiredError()
        files_in_memory = self._load_into_memory(files)
        submission_hash = self._hash(files_in_memory)
        existing = self.analysis_lookup_repository.find_by_hash(submission_hash)
        active_rubric = self.rubric_version_service.active_version() if self.rubric_version_service else None
        if existing and (active_rubric is None or active_rubric == existing.rubric_version):
            raise DuplicateSubmissionError(existing.analysis_id, existing.public_short_id)
        # Stub analysis
        short_id = self.short_id_generator.generate()
        target_hash = self._hash_target(delivery_target) if delivery_target else None
        analysis_id = self.analysis_stub_repository.create_stub(
            public_short_id=short_id,
            submission_hash=submission_hash,
            delivery_channel=delivery_channel,
            delivery_target_hash=target_hash,
            link_expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        # Create submission entity
        submission = ContractSubmission(
            submission_hash=submission_hash,
            public_short_id=short_id,
            file_count=len(files_in_memory),
            total_size_bytes=sum(f.size for f in files_in_memory),
            total_pages=self._estimate_pages(files_in_memory),
            file_formats=[f.format_short_code for f in files_in_memory],
            source=SubmissionSource.WEB,
            source_metadata=request_metadata,
            processing_status=ProcessingStatus.RECEIVED,
            analysis_id=analysis_id,
            disclaimer_accepted_at=datetime.now(timezone.utc),
            disclaimer_accepted_via=DisclaimerAcceptanceMethod.WEB_CHECKBOX,
            received_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
        # Persist
        saved = submission_handlers.create_submission(
            commands.CreateSubmission(submission=submission),
            self.submission_repository,
        )
        # Enqueue (Redis Streams; the payload holds an in-memory blob ref keyed by submission_id)
        self.stream_publisher.publish_received(submission_id=saved.id, files_in_memory=files_in_memory, force_strategy=force_strategy)
        return SubmissionAcceptedView(
            submission_id=saved.id,
            public_short_id=saved.public_short_id,
            analysis_id=saved.analysis_id,
            processing_status=saved.processing_status,
            estimated_completion_seconds=90,
            status_url=f"/v1/contracts/{saved.id}/status",
        )

    def accept_whatsapp_files(self, *, phone_hash: str, files: list, msg_id: str, disclaimer_accepted_at: datetime):
        """Mirror of accept_web_submission for the WhatsApp path."""
        ...

    def get_status(self, *, submission_id_or_short_id: str) -> "SubmissionStatusView | None":
        """Resolve UUID first, then short id; return a view DTO or None."""
        ...
```

**`ingestion/application/services/short_id_generator.py`**
```python
import secrets
from datetime import datetime
import base64


class ShortIdGenerator:
    """`CS-{YYYY}-{6 base32 chars}` (≥ 30 bits in suffix)."""

    def __init__(self, *, year_provider=None):
        self.year_provider = year_provider or (lambda: datetime.utcnow().year)

    def generate(self) -> str:
        year = self.year_provider()
        raw = secrets.token_bytes(4)
        suffix = base64.b32encode(raw).decode("ascii").rstrip("=")[:6].upper()
        return f"CS-{year}-{suffix}"
```

**`ingestion/infrastructure/django/repositories.py`**
```python
from datetime import datetime
from uuid import UUID
from django.db.models import QuerySet as DjangoQuerySet

from ingestion.domain.entities import ContractSubmission, OcrJob
from ingestion.infrastructure.django import models
from shared.infrastructure.django.repositories import DjangoFullRepository


class ContractSubmissionRepository(DjangoFullRepository[ContractSubmission, models.ContractSubmissionModel]):
    __model__ = models.ContractSubmissionModel

    def to_entity(self, model: models.ContractSubmissionModel) -> ContractSubmission:
        return ContractSubmission(
            id=model.pk,
            submission_hash=model.submission_hash,
            public_short_id=model.public_short_id,
            file_count=model.file_count,
            total_size_bytes=model.total_size_bytes,
            total_pages=model.total_pages,
            file_formats=list(model.file_formats),
            source=model.source,
            source_metadata=dict(model.source_metadata or {}),
            processing_status=model.processing_status,
            extraction_strategy_attempted=model.extraction_strategy_attempted,
            extraction_strategy_successful=model.extraction_strategy_successful,
            extracted_text_token_count=model.extracted_text_token_count,
            extracted_text_language=model.extracted_text_language,
            extracted_text_language_confidence=model.extracted_text_language_confidence,
            error_code=model.error_code,
            error_reason=model.error_reason,
            analysis_id=model.analysis_id,
            disclaimer_accepted_at=model.disclaimer_accepted_at,
            disclaimer_accepted_via=model.disclaimer_accepted_via,
            received_at=model.received_at,
            processing_started_at=model.processing_started_at,
            processing_completed_at=model.processing_completed_at,
            expires_at=model.expires_at,
        )

    def to_orm_model(self, entity: ContractSubmission) -> models.ContractSubmissionModel:
        if entity.id:
            m = self.__model__.objects.get(pk=entity.id)
        else:
            m = self.__model__()
        m.submission_hash = entity.submission_hash
        m.public_short_id = entity.public_short_id
        m.file_count = entity.file_count
        m.total_size_bytes = entity.total_size_bytes
        m.total_pages = entity.total_pages
        m.file_formats = list(entity.file_formats)
        m.source = entity.source
        m.source_metadata = entity.source_metadata
        m.processing_status = entity.processing_status
        m.extraction_strategy_attempted = entity.extraction_strategy_attempted
        m.extraction_strategy_successful = entity.extraction_strategy_successful
        m.extracted_text_token_count = entity.extracted_text_token_count
        m.extracted_text_language = entity.extracted_text_language
        m.extracted_text_language_confidence = entity.extracted_text_language_confidence
        m.error_code = entity.error_code
        m.error_reason = entity.error_reason
        m.analysis_id = entity.analysis_id
        m.disclaimer_accepted_at = entity.disclaimer_accepted_at
        m.disclaimer_accepted_via = entity.disclaimer_accepted_via
        m.received_at = entity.received_at
        m.processing_started_at = entity.processing_started_at
        m.processing_completed_at = entity.processing_completed_at
        m.expires_at = entity.expires_at
        return m

    def _optimize_queryset(self, queryset: DjangoQuerySet) -> DjangoQuerySet:
        return queryset  # no relations to prefetch

    def get_by_hash(self, submission_hash: str) -> ContractSubmission | None:
        m = self.__model__.objects.filter(submission_hash=submission_hash).first()
        return self.to_entity(m) if m else None

    def get_by_public_short_id(self, public_short_id: str) -> ContractSubmission | None:
        m = self.__model__.objects.filter(public_short_id=public_short_id).first()
        return self.to_entity(m) if m else None


class OcrJobRepository(DjangoFullRepository[OcrJob, models.OcrJobModel]):
    __model__ = models.OcrJobModel

    def to_entity(self, model: models.OcrJobModel) -> OcrJob:
        return OcrJob(
            id=model.pk,
            submission_id=model.submission_id,
            strategy=model.strategy,
            attempt_number=model.attempt_number,
            model_used=model.model_used,
            started_at=model.started_at,
            completed_at=model.completed_at,
            status=model.status,
            pages_processed=model.pages_processed,
            pages_failed=model.pages_failed,
            tokens_consumed=model.tokens_consumed,
            cost_estimate_cents=model.cost_estimate_cents,
            average_confidence=model.average_confidence,
            error_code=model.error_code,
            error_message=model.error_message,
            expires_at=model.expires_at,
        )

    def to_orm_model(self, entity: OcrJob) -> models.OcrJobModel:
        if entity.id:
            m = self.__model__.objects.get(pk=entity.id)
        else:
            m = self.__model__()
        m.submission_id = entity.submission_id
        m.strategy = entity.strategy
        m.attempt_number = entity.attempt_number
        m.model_used = entity.model_used
        m.started_at = entity.started_at
        m.completed_at = entity.completed_at
        m.status = entity.status
        m.pages_processed = entity.pages_processed
        m.pages_failed = entity.pages_failed
        m.tokens_consumed = entity.tokens_consumed
        m.cost_estimate_cents = entity.cost_estimate_cents
        m.average_confidence = entity.average_confidence
        m.error_code = entity.error_code
        m.error_message = entity.error_message
        m.expires_at = entity.expires_at
        return m


class AnalysisStubRepository:
    """Thin write-only wrapper for the contract_analysis stub row created at submit time.
    Lives in ingestion because the call site is ingestion-specific; it imports models from
    platform.infrastructure.django.models.ContractAnalysisModel.
    """

    def create_stub(self, *, public_short_id, submission_hash, delivery_channel, delivery_target_hash, link_expires_at) -> UUID:
        from platform.infrastructure.django.models import ContractAnalysisModel, ProjectModel
        placeholder = ProjectModel.objects.get(normalized_name="__unknown_pending__")
        ca = ContractAnalysisModel.objects.create(
            public_short_id=public_short_id,
            submission_hash=submission_hash,
            project=placeholder,
            contract_type="",  # filled by F2
            delivery_channel=delivery_channel,
            delivery_target_hash=delivery_target_hash,
            link_expires_at=link_expires_at,
            delivery_status="pending",
        )
        return ca.pk


class AnalysisLookupRepository:
    """Read-only lookup against the contract_analysis table for dedup decisions."""

    def find_by_hash(self, submission_hash: str):
        from platform.infrastructure.django.models import ContractAnalysisModel
        return (
            ContractAnalysisModel.objects
            .filter(submission_hash=submission_hash, anonymized_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
```

### Files to Modify

None for F1 in isolation. F8 must have created the placeholder project (`__unknown_pending__`) in its initial migration; F1 reads it via `AnalysisStubRepository`.

### API Endpoints

| Method | URL | Auth | Request | Response (2xx) | Response (4xx/5xx) |
|---|---|---|---|---|---|
| POST | `/v1/contracts/submit` | `AllowAny` + `BurstSubmitThrottle` | multipart (`files[]`, `disclaimer_accepted`, `delivery_channel`, `delivery_target`, `force_strategy`) | 201 `SubmissionAcceptedSerializer` | 400 `FORMAT_NOT_SUPPORTED`/`FILE_EMPTY`/`TOO_MANY_FILES`/`TOO_MANY_PAGES`/`IMAGE_DIMENSIONS_INVALID`/`DISCLAIMER_REQUIRED`/`INVALID_DELIVERY_CHANNEL`/`INVALID_DELIVERY_TARGET`/`PDF_NOT_SAFE`, 409 duplicate, 413 `FILE_TOO_LARGE`/`TOTAL_SIZE_TOO_LARGE`, 429 `RATE_LIMITED`, 500 internal |

### Implementation Order

1. Implement domain entities, enums, exceptions
2. Implement commands, queries, message envelopes
3. Implement handlers (pure functions over repositories)
4. Implement repositories paired with the F8 Django models
5. Implement `ShortIdGenerator`
6. Implement `IngestionService.accept_web_submission`
7. Implement serializers, throttles, viewset, URLs
8. Implement Redis stream publisher
9. Implement the Celery task `process_submission`
10. Wire DRF custom exception handler to translate `DomainException` to JSON

### Security Notes

- `AllowAny` permission (Casa Segura has no users); HTTP throttling is the abuse defense
- `delivery_target` is hashed (salt+sha256) before persistence in `delivery_target_hash`; the cleartext is held only in memory long enough to be encrypted by F7 when the `DeliveryRequest` is created
- Source metadata (IP, UA, phone) is hashed before storage; no raw PII
- Multipart file reads cap memory: streaming `request.FILES['files']` is fine because Django writes large bodies to a temp file by default — F1 enforces a configured `DATA_UPLOAD_MAX_MEMORY_SIZE` and `FILE_UPLOAD_MAX_MEMORY_SIZE` and rejects beyond 15 MB per file before reading content
- After successful enqueue, the in-memory blob is held in Redis (key TTL ≤ 300 s) only long enough for the worker to consume; never written to disk

### Test Cases to Write

- [ ] Valid PDF only → 201 with submission_id and short_id
- [ ] Valid mixed files (one PDF + 3 images) → 201
- [ ] `disclaimer_accepted=false` → 400 `DISCLAIMER_REQUIRED`
- [ ] `.docx` in upload → 400 `FORMAT_NOT_SUPPORTED`
- [ ] 16 MB PDF → 413 `FILE_TOO_LARGE`
- [ ] 51 files → 400 `TOO_MANY_FILES`
- [ ] 81 pages total → 400 `TOO_MANY_PAGES`
- [ ] PDF with JS → 400 `PDF_NOT_SAFE`
- [ ] Duplicate hash same rubric → 409
- [ ] Duplicate hash different rubric → 201 new submission
- [ ] Rate limit (6th submit in an hour) → 429
- [ ] Concurrent submissions of same file converge to same `analysis_id`

---

## Story: US-02 — User sends the contract via WhatsApp

### Acceptance Criteria

- 5-minute Redis session aggregates files
- Affirmative disclaimer required
- Session closes on "listo" or timeout
- Same validation rules as US-01

### Dependencies

- US-01
- F7 (Zavu credentials and approved templates)

### Files to Create

**`ingestion/infrastructure/django/views.py`** — *Webhook view* (separate from the public viewset)
```python
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from shared.infrastructure.django.permissions import ValidatesZavuSignature


class ZavuWebhookView(APIView):
    permission_classes = [AllowAny]  # signature check is enforced as a pre-handler

    whatsapp_session_manager = WhatsAppSessionManager(session_store=SessionStore())
    ingestion_service = IngestionService(...)  # share instance via DI factory

    def post(self, request):
        signature = request.headers.get("X-Zavu-Signature", "")
        if not ValidatesZavuSignature.verify(request.body, signature):
            return Response({"error": "invalid_signature"}, status=401)
        payload = serializers.ZavuWebhookPayloadSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        self._route(payload.validated_data)
        return Response({"status": "received"})

    def _route(self, payload):
        # Branch on payload type: media | text | command (listo/cancelar/etc.)
        ...
```

**`ingestion/infrastructure/django/urls_zavu.py`**
```python
from django.urls import path
from ingestion.infrastructure.django.views import ZavuWebhookView

urlpatterns = [
    path("webhook", ZavuWebhookView.as_view(), name="zavu-webhook"),
]
```

**`ingestion/application/services/whatsapp_session.py`** — Session manager
**`ingestion/application/services/disclaimer_recognition.py`** — `classify_message(text)` → intent
**`ingestion/infrastructure/external/zavu_client.py`** — HMAC verifier, signed-URL downloader, template sender
**`ingestion/infrastructure/redis/session_store.py`** — Redis-backed session
**`ingestion/infrastructure/redis/keyspace_listener.py`** — Subscribes to `__keyevent@0__:expired`

### API Endpoints

| Method | URL | Auth | Request | Response (2xx) | Response (4xx/5xx) |
|---|---|---|---|---|---|
| POST | `/v1/zavu/webhook` | HMAC `X-Zavu-Signature` | `ZavuWebhookPayload` | 200 `{"status":"received"}` | 401 invalid signature |

### Security Notes

- HMAC constant-time compare via `hmac.compare_digest`
- Phone hashing uses global salt env var `PHONE_HASH_SALT`
- Zavu signed URLs have short TTL; download in-memory only

### Test Cases

- [ ] Valid signature + first photo → new session, welcome sent
- [ ] Invalid signature → 401, no side effects
- [ ] Disclaimer accepted + photos + "listo" → submission created
- [ ] 5-minute timeout → submission created if disclaimer accepted; otherwise instructed to retry
- [ ] "cancelar" → session destroyed, no submission
- [ ] > 50 files mid-session → force-close + warning
- [ ] Unsupported format → reply with error, session stays open
- [ ] 4th submission in an hour from same phone → reply with rate-limit message

---

## Story: US-03 — System validates submission and deduplicates by hash

### Acceptance Criteria

- SHA-256 over concatenated per-file hashes sorted by filename
- Lookup against `contract_analysis.submission_hash` (excluding anonymized)
- Same active rubric → return prior; different → new analysis

### Files to Create / Modify

`ingestion/application/services/ingestion_service.py` — `_hash()` and `_check_dedup()` helpers
`ingestion/infrastructure/django/repositories.py` — `AnalysisLookupRepository.find_by_hash`

### Implementation Order

1. Hash deterministically (sort by original filename ASCII)
2. Query existing rubric+corpus active versions via `platform`
3. Compare → branch

### Test Cases

- [ ] Same bytes twice → 409 with same `public_short_id`
- [ ] Same bytes different rubric → 201
- [ ] Filename reorder yields same hash
- [ ] Anonymized prior analysis is ignored

---

## Story: US-04 — System chooses extraction strategy

### Files to Create

**`ingestion/application/services/extraction_orchestrator.py`** (plain class)
**`ingestion/infrastructure/ocr/base.py`** (`ExtractionStrategy` `Protocol`)

### Test Cases

- [ ] PDF with text on page 1 → `pypdf`
- [ ] PDF with no text on page 1 → `vision_llm`
- [ ] JPEG/PNG/HEIC/WEBP → `vision_llm`
- [ ] Mixed submission: each file processed with its own strategy; texts concatenated
- [ ] `force_strategy=tesseract` honored
- [ ] `OCR_COST_SAVER_MODE=true` → images go to Tesseract first

---

## Story: US-05 — pypdf extraction

**`ingestion/infrastructure/ocr/pypdf_extractor.py`** — see PRD §3 US-05.

### Test Cases

- [ ] Native text PDF → text + separators
- [ ] PDF with embedded images and no text → `diagnose` returns False
- [ ] Encrypted PDF → `PDF_ENCRYPTED`
- [ ] Timeout → `TIMEOUT`
- [ ] Text < 500 chars → suggests escalation

---

## Story: US-06 — Vision LLM extraction

**`ingestion/infrastructure/ocr/vision_llm_extractor.py`** — Implements PRD §3 US-06 with prompts from §8.1 and §8.2.
**`ingestion/infrastructure/llm/openrouter_client.py`** — Circuit-breaker-wrapped client. Uses `httpx` sync (called from Celery task context).

```python
# Configuration: idempotency key format submission_id:p{N}:vision_llm:a{attempt}
# Concurrency: per-page in series (PRD F1 §3 US-06)
```

### Test Cases

- [ ] 12/12 pages succeed → success
- [ ] 4/12 fail → suggests fallback
- [ ] 3/12 fail → success with `pages_failed=3`
- [ ] 503 then 200 with same idempotency key → success
- [ ] 401 from OpenRouter → `LLM_AUTH_FAILED`
- [ ] Circuit breaker open → fast-fail
- [ ] Total 5-minute timeout → cancelled

---

## Story: US-07 — Tesseract fallback

**`ingestion/infrastructure/ocr/tesseract_extractor.py`** — preprocesses image, runs `pytesseract.image_to_data`, checks confidence.

### Test Cases

- [ ] Clean scan → avg conf ≥ 60
- [ ] Poor scan → avg conf < 60
- [ ] Per-page timeout
- [ ] Spanish language pack present/absent

---

## Story: US-08 — Language detection

**`ingestion/infrastructure/ocr/language_detector.py`** — uses `langdetect` (default) or `lingua-py`.

### Test Cases

- [ ] Pure Spanish → `("es", >0.95)`
- [ ] Mixed Spanish/English → `("es", 0.85–0.95)`
- [ ] Pure English → `("en", >0.85)`
- [ ] Very short text → low confidence

---

## Story: US-09 — Status endpoint

Lives on the same `SubmissionViewSet` as US-01 (`@action(detail=True, methods=["get"], url_path="status")`).

### Test Cases

- [ ] By UUID → view
- [ ] By short id (`CS-2026-A1B2C3`) → view
- [ ] Unknown → 404
- [ ] Mid-extraction → progress fields
- [ ] `rejected_language` → translated message

---

## Story: US-10 — Discard original files after processing

The Celery task `process_submission` discards all blob refs in a `finally` block. The Redis blob key is set with `EX 300` and explicitly `DEL`'d in `finally` regardless of outcome.

### Test Cases (smoke / structural)

- [ ] After a submission completes, no file under `/tmp/casa_segura/*`
- [ ] After failure, no Redis key matches `blob:submission:{id}:*`
- [ ] The audit script verifies no code path writes `bytes` to a model field

---

## Part 2 — Staged Execution Plan

### Codebase Alignment Rules (recap from `_shared/GLOBAL_ASSUMPTIONS.md`)

- Django 5.2 LTS + DRF + DDD/CQRS per `architecture-conventions.md`
- Module path: `ingestion/{domain,application,infrastructure}/`
- All models inherit nothing in particular for F1 transient tables (no soft delete, no auto timestamps via mixin — `received_at` and `expires_at` are explicit fields). The skill mandate `SoftDeleteObject, ModelWithTimeStamps` applies to persistent business tables (Project, ContractAnalysis, catalogs) defined in other modules. F1's transient tables are an exception **documented in `EVALUATION_COVERAGE.md` Q-F1-01**.
- Repositories: `DjangoFullRepository[T, K]` from `shared.infrastructure.django.repositories`
- Services: plain classes with repos injected via `__init__(*, ...=...)`
- Views: services and repositories as class-level attributes; explicit `permission_classes`; `@extend_schema`
- Serializers: never `fields = '__all__'`
- All env vars under `F1_*` namespace
- Celery tasks: `@shared_task(name="ingestion.<name>")`; accept IDs only
- All fields in Django models include `help_text=...`

### Stage Overview

| # | Stage Name | Deliverable | Depends On |
|---|---|---|---|
| 1 | Domain entities and enums | Pydantic models, enums, exceptions | — |
| 2 | Commands and queries | CQRS commands/queries + envelopes | Stage 1 |
| 3 | Handler functions | Pure functions over `(command|query, repository)` | Stage 2 |
| 4 | Service classes | `IngestionService`, `ExtractionOrchestrator`, `WhatsAppSessionManager` | Stage 3 |
| 5 | Django ORM models and migration | `ContractSubmissionModel`, `OcrJobModel` | F8 schema baseline |
| 6 | Repositories | `ContractSubmissionRepository`, `OcrJobRepository`, `AnalysisStubRepository`, `AnalysisLookupRepository` | Stages 4 + 5 |
| 7 | DRF serializers and throttles | Request/response serializers, `BurstSubmitThrottle`, `WhatsAppSubmitThrottle` | Stage 6 |
| 8 | DRF views and URLs | `SubmissionViewSet`, `ZavuWebhookView`, URL routers | Stages 6 + 7 |
| 9 | OCR strategies | `PyPdfExtractor`, `VisionLlmExtractor`, `TesseractExtractor`, `LanguageDetector` | Stage 4 |
| 10 | External clients | `OpenRouterClient` (with circuit breaker), `ZavuClient`, `SessionStore` | Stage 4 |
| 11 | Redis publisher + Celery task | `SubmissionStreamPublisher`, `@shared_task process_submission`, keyspace listener | Stages 8 + 9 + 10 |
| 12 | Periodic task | `@shared_task mark_stuck_submissions` registered with django-celery-beat | Stage 11 |
| 13 | Test cases | Unit + integration + smoke tests | All |
| 14 | Observability | Prometheus metrics, structured logging | Stage 11 |
| 15 | Documentation | README.md for `ingestion/` + ops runbook | All |

### Stage 1: Domain entities and enums

**Goal:** The domain layer compiles, has zero framework dependencies, and is fully unit-tested.

**Estimated scope:** S

#### Deliverables

- [ ] `ingestion/domain/entities.py`
- [ ] `ingestion/domain/enums.py` (TextChoices)
- [ ] `ingestion/domain/exceptions.py` (subclasses of `common.domain.exceptions.core.DomainException`)

#### Reference Code

```python
# ingestion/domain/exceptions.py
from uuid import UUID
from common.domain.exceptions.core import DomainException


class IngestionDomainException(DomainException):
    """Base for F1 errors."""


class DisclaimerRequiredError(IngestionDomainException):
    def __init__(self) -> None:
        super().__init__(message="Acepta el disclaimer para continuar.", code="DISCLAIMER_REQUIRED", status=400)


class FormatNotSupportedError(IngestionDomainException):
    def __init__(self, rejected_files: list[str]) -> None:
        super().__init__(
            message="Solo aceptamos PDF, JPG, PNG, HEIC, o WEBP.",
            code="FORMAT_NOT_SUPPORTED", status=400, extra={"rejected_files": rejected_files},
        )


class DuplicateSubmissionError(IngestionDomainException):
    def __init__(self, analysis_id: UUID, public_short_id: str) -> None:
        super().__init__(
            message="Este contrato ya fue analizado previamente.",
            code="DUPLICATE_SUBMISSION", status=409,
            extra={"analysis_id": str(analysis_id), "public_short_id": public_short_id, "is_duplicate": True},
        )
```

#### Acceptance Criteria

- [ ] `mypy --strict ingestion/domain` passes
- [ ] `pytest ingestion/domain` passes
- [ ] No import from `infrastructure` or `application` or any framework

### Stage 2: Commands, queries, envelopes

#### Deliverables

- [ ] `ingestion/application/commands.py`
- [ ] `ingestion/application/queries.py`
- [ ] `ingestion/application/contracts/messages.py`

### Stage 3: Handler functions

```python
# ingestion/application/handlers/submission_handlers.py
from ingestion.application import commands
from ingestion.domain.entities import ContractSubmission
from shared.domain.entities import repositories as shared_repositories


def create_submission(
    command: commands.CreateSubmission,
    repository: shared_repositories.BaseRepository[ContractSubmission],
) -> ContractSubmission:
    return repository.save(command.submission)


def update_status(
    command: commands.UpdateSubmissionStatus,
    repository: shared_repositories.BaseRepository[ContractSubmission],
) -> ContractSubmission:
    submission = repository.get(criteria={"id": command.submission_id})
    submission.processing_status = command.new_status
    if command.extraction_strategy_attempted is not None:
        submission.extraction_strategy_attempted = command.extraction_strategy_attempted
    # ... apply other set fields
    return repository.update(submission)
```

### Stage 4: Service classes

#### Deliverables

- [ ] `ingestion/application/services/ingestion_service.py`
- [ ] `ingestion/application/services/extraction_orchestrator.py`
- [ ] `ingestion/application/services/whatsapp_session.py`
- [ ] `ingestion/application/services/disclaimer_recognition.py`
- [ ] `ingestion/application/services/short_id_generator.py`

#### Acceptance Criteria

- [ ] All service classes have `__init__(*, ...)` with explicit keyword-only repository dependencies, matching the conventions
- [ ] Unit tests run with mocked repos, mocked extractors, mocked stream publisher

### Stage 5: Django ORM models and migration

**Note:** the DDL for `contract_submission` and `ocr_job` is defined globally in F8. F1 declares the Django model classes that *map* to the F8 tables. F1's `apps.py` uses `label="ingestion"` so the migration directory is `ingestion/infrastructure/django/migrations/`. The first F1 migration is empty (no model added) — the actual table is created by F8's migration. We register the Django model in F1's app for ORM access but list `managed = False` in `Meta` so Django does not try to create or alter the table from F1 migrations.

**Decision (documented in `EVALUATION_COVERAGE.md` Q-F1-02)**: All persistent tables live in a single Django app (`platform`) for migration cohesion, but each module's `infrastructure.django.models` imports the relevant model classes from `platform.infrastructure.django.models` and re-exports them as feature-local aliases for code readability. Repositories use the imported model directly. This avoids cross-app FK issues and keeps `makemigrations` clean.

#### Deliverables

- [ ] `ingestion/infrastructure/django/models.py` — re-exports `ContractSubmissionModel`, `OcrJobModel` from `platform.infrastructure.django.models`
- [ ] `ingestion/infrastructure/django/admin.py` — registers read-only admin views for transient tables
- [ ] `ingestion/infrastructure/django/apps.py` — `IngestionConfig`

#### Reference Code

```python
# ingestion/infrastructure/django/models.py
# Models live in platform; re-exported here for feature-local imports.
from platform.infrastructure.django.models import (
    ContractSubmissionModel,
    OcrJobModel,
)

__all__ = ["ContractSubmissionModel", "OcrJobModel"]
```

```python
# platform/infrastructure/django/models.py  (defined fully in F8 plan; excerpt relevant to F1)
from django.contrib.postgres.fields import ArrayField
from django.db import models
from common.infrastructure.django.models import ModelWithTimeStamps
from ingestion.domain.enums import (
    ProcessingStatus, ExtractionStrategy, OcrJobStatus,
    SubmissionSource, DisclaimerAcceptanceMethod,
)


class ContractSubmissionModel(models.Model):
    """Transient — 24-hour retention. Owned by F1. Cleaned up by F8 cron."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Internal identifier")
    submission_hash = models.TextField(help_text="SHA-256 of concatenated per-file hashes ordered by filename.", db_index=True)
    public_short_id = models.TextField(unique=True, help_text="Short ID visible to the user (format CS-YYYY-XXXXXX).")
    file_count = models.IntegerField(help_text="Number of files in this submission (1..50).")
    total_size_bytes = models.BigIntegerField(help_text="Sum of file sizes in bytes.")
    total_pages = models.IntegerField(null=True, help_text="Total pages (PDF pages + image count).")
    file_formats = ArrayField(models.CharField(max_length=8), help_text="Short codes per file: pdf, jpg, png, heic, webp.")
    source = models.CharField(max_length=16, choices=SubmissionSource.choices, help_text="Channel of origin.")
    source_metadata = models.JSONField(default=dict, help_text="Hashed audit fields; never raw PII.")
    processing_status = models.CharField(max_length=32, choices=ProcessingStatus.choices, default=ProcessingStatus.RECEIVED, db_index=True, help_text="Current pipeline state.")
    extraction_strategy_attempted = models.CharField(max_length=16, choices=ExtractionStrategy.choices, null=True, help_text="First strategy chosen by the orchestrator.")
    extraction_strategy_successful = models.CharField(max_length=16, choices=ExtractionStrategy.choices, null=True, help_text="Strategy that returned usable text.")
    extracted_text_token_count = models.IntegerField(null=True, help_text="tiktoken cl100k_base count of extracted text. Never the text itself.")
    extracted_text_language = models.CharField(max_length=8, null=True, help_text="Detected language ISO 639-1 code.")
    extracted_text_language_confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, help_text="Language detection confidence 0..1.")
    error_code = models.CharField(max_length=64, null=True, help_text="Normalized error code on failure.")
    error_reason = models.TextField(null=True, help_text="Operator-facing reason on failure.")
    analysis_id = models.UUIDField(null=True, db_index=True, help_text="FK to the ContractAnalysis stub created at submit time.")
    disclaimer_accepted_at = models.DateTimeField(help_text="Time the user accepted the legal-advice disclaimer.")
    disclaimer_accepted_via = models.CharField(max_length=16, choices=DisclaimerAcceptanceMethod.choices, help_text="Channel of disclaimer acceptance.")
    received_at = models.DateTimeField(auto_now_add=True, help_text="Server clock at submit time.")
    processing_started_at = models.DateTimeField(null=True, help_text="Worker pickup time.")
    processing_completed_at = models.DateTimeField(null=True, help_text="Worker terminal time.")
    expires_at = models.DateTimeField(db_index=True, help_text="Time the row becomes eligible for hard delete by F8 cron.")

    class Meta:
        db_table = "contract_submission"
        managed = True  # owned by F8 app
        constraints = [
            models.CheckConstraint(check=models.Q(file_count__gte=1, file_count__lte=50), name="contract_submission_file_count_range"),
            models.CheckConstraint(
                check=models.Q(processing_status="completed", analysis_id__isnull=False) | ~models.Q(processing_status="completed"),
                name="contract_submission_analysis_required_when_completed",
            ),
        ]
        indexes = [
            models.Index(fields=["submission_hash"], name="idx_submission_hash"),
            models.Index(fields=["processing_status"], name="idx_submission_status"),
            models.Index(fields=["expires_at"], name="idx_submission_expires"),
            models.Index(fields=["public_short_id"], name="idx_submission_public_short"),
        ]

    def __str__(self) -> str:
        return f"ContractSubmission {self.public_short_id} ({self.processing_status})"


class OcrJobModel(models.Model):
    """Transient — 24-hour retention. ON DELETE CASCADE from ContractSubmission."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, help_text="Internal identifier")
    submission = models.ForeignKey(ContractSubmissionModel, on_delete=models.CASCADE, related_name="ocr_jobs", help_text="Owning submission.")
    strategy = models.CharField(max_length=16, choices=ExtractionStrategy.choices, help_text="OCR strategy attempted by this job.")
    attempt_number = models.IntegerField(default=1, help_text="Retry attempt within this strategy (≥ 1).")
    model_used = models.CharField(max_length=128, null=True, help_text="OpenRouter model id for vision_llm jobs (e.g. anthropic/claude-sonnet-4).")
    started_at = models.DateTimeField(auto_now_add=True, help_text="When the job started.")
    completed_at = models.DateTimeField(null=True, help_text="When the job ended (success or failure).")
    status = models.CharField(max_length=16, choices=OcrJobStatus.choices, db_index=True, help_text="Terminal state.")
    pages_processed = models.IntegerField(null=True, help_text="Pages that returned valid text.")
    pages_failed = models.IntegerField(null=True, help_text="Pages where extraction failed.")
    tokens_consumed = models.IntegerField(null=True, help_text="LLM tokens consumed (vision_llm only).")
    cost_estimate_cents = models.IntegerField(null=True, help_text="Estimated USD cents charged by the LLM provider.")
    average_confidence = models.DecimalField(max_digits=4, decimal_places=2, null=True, help_text="Mean per-token confidence (tesseract only).")
    error_code = models.CharField(max_length=64, null=True, help_text="Normalized error code.")
    error_message = models.TextField(null=True, help_text="Operator-facing failure message.")
    expires_at = models.DateTimeField(db_index=True, help_text="Time the row becomes eligible for hard delete by F8 cron.")

    class Meta:
        db_table = "ocr_job"
        managed = True
        constraints = [
            models.CheckConstraint(check=models.Q(attempt_number__gte=1), name="ocr_job_attempt_positive"),
        ]
        indexes = [
            models.Index(fields=["submission"], name="idx_ocr_job_submission"),
            models.Index(fields=["status"], name="idx_ocr_job_status"),
            models.Index(fields=["expires_at"], name="idx_ocr_job_expires"),
        ]

    def __str__(self) -> str:
        return f"OcrJob {self.id} ({self.strategy}, {self.status})"
```

**Note**: The `managed = True` location matters. The model is *declared* under the `platform` app (the F8 module owns the migration), and F1's `models.py` re-imports the same class. Django will list it under `platform_app_label`'s migrations. F1's own migration directory stays empty. This matches the architecture-conventions philosophy that one app owns the schema for related tables.

### Stage 6: Repositories

#### Deliverables

- [ ] `ingestion/infrastructure/django/repositories.py` (Section "Files to Create" above)
- [ ] Repository tests against `pytest-django` with savepoint isolation
- [ ] `factory-boy` factories under `ingestion/tests/factories.py`

### Stage 7: DRF serializers and throttles

#### Deliverables

- [ ] `ingestion/infrastructure/django/serializers.py` (Section above)
- [ ] `ingestion/infrastructure/django/throttles.py`
- [ ] `ingestion/infrastructure/django/exception_handler.py` — maps `DomainException` → DRF `Response(status=exc.status_code, data={"error": {"code": exc.code, "message": exc.message, "details": exc.extra}})`. Registered in `REST_FRAMEWORK = {"EXCEPTION_HANDLER": "shared.infrastructure.django.exception_handler.domain_exception_handler"}`.

### Stage 8: DRF views and URLs

#### Deliverables

- [ ] `ingestion/infrastructure/django/views.py` (`SubmissionViewSet`, `ZavuWebhookView`, `InternalRetryView`)
- [ ] `ingestion/infrastructure/django/urls.py`
- [ ] `ingestion/infrastructure/django/urls_zavu.py`

### Stage 9: OCR strategies

#### Deliverables

- [ ] `ingestion/infrastructure/ocr/base.py` (`Protocol`)
- [ ] `ingestion/infrastructure/ocr/pypdf_extractor.py`
- [ ] `ingestion/infrastructure/ocr/vision_llm_extractor.py`
- [ ] `ingestion/infrastructure/ocr/tesseract_extractor.py`
- [ ] `ingestion/infrastructure/ocr/language_detector.py`

### Stage 10: External clients

#### Deliverables

- [ ] `ingestion/infrastructure/llm/openrouter_client.py` (with `CircuitBreaker` from `shared.infrastructure.resilience`)
- [ ] `ingestion/infrastructure/llm/pricing.py`
- [ ] `ingestion/infrastructure/external/zavu_client.py`
- [ ] `ingestion/infrastructure/redis/session_store.py`
- [ ] `ingestion/infrastructure/redis/stream_publisher.py`
- [ ] `shared/infrastructure/resilience/circuit_breaker.py` (reused by F7)
- [ ] `shared/infrastructure/django/permissions.py` — `HasInternalAuthHeader`, `ValidatesZavuSignature`, `IsCapabilityHolder`

### Stage 11: Celery task + Redis Streams consumer

#### Deliverables

- [ ] `ingestion/infrastructure/celery/ingestion_tasks.py`

```python
# ingestion/infrastructure/celery/ingestion_tasks.py
from celery import shared_task
from ingestion.application.services.ingestion_service import IngestionService
from ingestion.application.services.extraction_orchestrator import ExtractionOrchestrator
# ... imports for repositories, extractors, language detector

@shared_task(name="ingestion.process_submission", bind=True, max_retries=2)
def process_submission(self, submission_id: str) -> None:
    """Worker entry-point. Loads the submission, runs extraction, publishes to F2 queue.
    The in-memory file bytes are read from Redis using the blob ref stored at submit time
    (key TTL ≤ 300s). On any terminal outcome the Redis blob key is DEL'd."""
    service = IngestionService(...)
    service.process_submission(submission_id=submission_id)


@shared_task(name="ingestion.mark_stuck_submissions")
def mark_stuck_submissions() -> dict:
    """Cron: marks submissions in 'received'|'extracting'|'classifying' for > 1 hour as 'expired'."""
    from datetime import datetime, timedelta, timezone
    from platform.infrastructure.django.models import ContractSubmissionModel
    threshold = datetime.now(timezone.utc) - timedelta(hours=1)
    count = ContractSubmissionModel.objects.filter(
        processing_status__in=["received", "extracting", "classifying"],
        processing_started_at__lt=threshold,
    ).update(processing_status="expired", error_code="STUCK_IN_PROCESSING", error_reason="Submission stuck in processing")
    return {"marked_expired": count}
```

- [ ] `ingestion/infrastructure/redis/stream_publisher.py` — wraps `redis.Redis.xadd("ingestion.to_classification", payload)`
- [ ] `ingestion/infrastructure/redis/keyspace_listener.py` — process subscribing to `__keyevent@0__:expired` for `whatsapp_session:*` (runs as a separate daemon, not a Celery task — Celery does not natively support Redis keyspace notifications)

### Stage 12: Periodic task

`django-celery-beat` schedules `ingestion.mark_stuck_submissions` every hour. Schedule is created at AppConfig.ready() via `PeriodicTask` and `IntervalSchedule` ORM objects.

### Stage 13: Tests

- Unit tests per service / per extractor (mocked deps)
- Integration tests: end-to-end submit → extract → enqueue, using a test Postgres and a fake OpenRouter via `respx`
- Smoke test that no file persists to disk after a submission completes
- Throttle test that 6th request inside an hour returns 429
- Coverage target ≥ 85% for `ingestion/`

### Stage 14: Observability

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `f1_submission_received_total` | Counter | `source` | Throughput |
| `f1_submission_outcome_total` | Counter | `outcome` | Funnel |
| `f1_extraction_latency_seconds` | Histogram | `strategy` | Per-strategy latency |
| `f1_extraction_cost_cents_total` | Counter | `strategy`, `model` | Cost burn |
| `f1_extraction_tokens_total` | Counter | `strategy`, `model` | Tokens burn |
| `f1_extraction_pages_total` | Counter | `strategy`, `outcome` | Pages processed |
| `f1_dedup_hits_total` | Counter | — | How often dedup saves an analysis |
| `f1_circuit_breaker_state` | Gauge | `target` | Breaker state |
| `f1_whatsapp_sessions_open` | Gauge | — | Sessions in flight |
| `f1_language_rejection_total` | Counter | `detected_language` | Rejected-by-language by language |

`django-prometheus` exports these via `/metrics`. Celery workers also push to the same registry via a sidecar process or `prometheus_client.multiprocess`.

### Stage 15: Documentation

- [ ] `ingestion/README.md`
- [ ] Ops runbook entry in `docs/RUNBOOK.md` covering: stuck submissions, OpenRouter breaker tripping, Tesseract pack missing in worker image

---

## Error Codes (canonical list owned by F1)

| Code | HTTP | Description |
|---|---|---|
| `FORMAT_NOT_SUPPORTED` | 400 | Unsupported MIME |
| `FILE_TOO_LARGE` | 413 | Per-file > 15 MB |
| `TOTAL_SIZE_TOO_LARGE` | 413 | Submission > 100 MB |
| `FILE_EMPTY` | 400 | < 1 KB |
| `TOO_MANY_FILES` | 400 | > 50 files |
| `TOO_MANY_PAGES` | 400 | > 80 pages |
| `IMAGE_DIMENSIONS_INVALID` | 400 | Image outside accepted range |
| `DISCLAIMER_REQUIRED` | 400 | Disclaimer flag missing |
| `PDF_NOT_SAFE` | 400 | PDF with JS or interactive forms |
| `INVALID_DELIVERY_CHANNEL` | 400 | Channel not in enum |
| `INVALID_DELIVERY_TARGET` | 400 | Email/phone format fails |
| `RATE_LIMITED` | 429 | Throttle exceeded |
| `LANGUAGE_NOT_SUPPORTED` | 422 | Language ≠ es |
| `TEXT_TOO_SHORT` | 422 | < 500 chars after normalization |
| `EXTRACTION_FAILED` | 500 | All strategies failed |
| `LLM_AUTH_FAILED` | — | Internal; surfaced as 500 |
| `TIMEOUT_EXCEEDED` | 504/422 | > 5 min total |
| `INVALID_SIGNATURE` | 401 | Zavu webhook HMAC mismatch |
| `SUBMISSION_NOT_FOUND` | 404 | Not found / expired |
| `STUCK_IN_PROCESSING` | — | Cron marker |
| `DUPLICATE_SUBMISSION` | 409 | Same hash + active rubric |
| `EXTRACTION_FILES_GONE` | 422 | Original bytes no longer in memory |

---

## Configuration matrix (all F1 env vars)

| Variable | Default | Purpose |
|---|---|---|
| `F1_MAX_FILE_SIZE_MB` | 15 | Per-file cap |
| `F1_MAX_TOTAL_SIZE_MB` | 100 | Submission cap |
| `F1_MAX_FILES` | 50 | Count cap |
| `F1_MAX_PAGES` | 80 | Page cap |
| `F1_RATE_LIMIT_WEB_PER_HOUR` | 5 | Per-IP throttle (`BurstSubmitThrottle.rate`) |
| `F1_RATE_LIMIT_WHATSAPP_PER_HOUR` | 3 | Per-phone throttle |
| `F1_SUBMISSION_TIMEOUT_SECONDS` | 300 | Per-submission OCR budget |
| `OCR_VISION_MODEL` | `anthropic/claude-sonnet-4` | OpenRouter model |
| `OCR_VISION_DPI` | 150 | PDF→JPEG resolution |
| `OCR_VISION_MAX_IMAGE_DIM_PX` | 1920 | Clamp longest side |
| `OCR_VISION_TIMEOUT_PER_PAGE_SECONDS` | 60 | LLM page timeout |
| `OCR_VISION_MAX_RETRIES_PER_PAGE` | 2 | LLM retries |
| `OCR_VISION_PARTIAL_FAILURE_THRESHOLD` | 0.30 | Fallback trigger |
| `OCR_TESSERACT_ENABLED` | `true` | Fallback enabled |
| `OCR_TESSERACT_LANGUAGE` | `spa` | Tesseract language pack |
| `OCR_TESSERACT_MIN_CONFIDENCE` | 60 | Quality threshold |
| `OCR_COST_SAVER_MODE` | `false` | Prefer Tesseract |
| `OCR_LANGUAGE_DETECTOR` | `langdetect` | Detector backend |
| `OCR_LANGUAGE_CONFIDENCE_THRESHOLD` | 0.85 | Reject threshold |
| `OCR_MIN_EXTRACTED_TEXT_CHARS` | 500 | Re-escalate if shorter |
| `OPENROUTER_API_KEY` | — | Required |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | API root |
| `OPENROUTER_HTTP_REFERER` | `https://casasegura.sv` | OpenRouter header |
| `OPENROUTER_X_TITLE` | `Casa Segura` | OpenRouter header |
| `OPENROUTER_CB_FAILURE_THRESHOLD` | 5 | Circuit breaker trigger |
| `OPENROUTER_CB_TIME_WINDOW_SECONDS` | 60 | Window |
| `OPENROUTER_CB_OPEN_DURATION_SECONDS` | 300 | Cool-off |
| `ZAVU_API_BASE_URL` | `https://api.zavu.com/v1` | — |
| `ZAVU_API_KEY` | — | Required |
| `ZAVU_WEBHOOK_SECRET` | — | HMAC secret |
| `ZAVU_PHONE_NUMBER_ID` | — | WhatsApp Business number id |
| `PHONE_HASH_SALT` | — | Salt for phone hashing |
| `REDIS_URL` | — | Required |
| `REDIS_STREAM_INGESTION_TO_CLASSIFICATION` | `ingestion.to_classification` | Stream name |
| `WHATSAPP_SESSION_TTL_SECONDS` | 300 | Session live time |
| `STUCK_SUBMISSION_THRESHOLD_MINUTES` | 60 | Periodic threshold |
| `CELERY_BROKER_URL` | uses `REDIS_URL` | Celery broker |
| `CELERY_RESULT_BACKEND` | uses `REDIS_URL` | Celery result backend |
| `CELERY_TASK_DEFAULT_QUEUE` | `default` | — |
| `LOG_LEVEL` | `INFO` | Structured logging |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | `15728640` (15 MB) | Django setting; enforced per-file |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | `15728640` | Django setting |

---

**End of document.**
