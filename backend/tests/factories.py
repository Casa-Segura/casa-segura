"""factory_boy factories for every Casa Segura entity (CS-032).

Coverage: Project, ContractAnalysis, ContractSubmission, OcrJob,
DeliveryRequest, RubricVersion, Criterion, CorpusVersion, LegalDocument,
LegalChunk (with dim-384 vector generator), BenchmarkVersion,
EconomicBenchmark.

Helpers exposed at module top:
    - `random_vector_384()`     — deterministic dim-384 float vector for LegalChunk
    - `make_public_short_id()`  — string matching DOMAIN `CS-YYYY-XXXXXX` format
    - `age_to(ts)` / `expire_in(delta)` — for retention-view fixtures (CS-030)

All factories return saved instances by default (`factory.django.DjangoModelFactory`).
Use `.build()` (no save) when constructing rows that will fail constraints
on purpose."""

from __future__ import annotations

import random
import secrets
import string
from datetime import datetime, timedelta
from decimal import Decimal

import factory
import factory.fuzzy

from django.utils import timezone

from corpus.domain.enums import LegalDocumentStatus, SeverityHint
from corpus.infrastructure.django.models import (
    EMBEDDING_DIM,
    CorpusVersion,
    LegalChunk,
    LegalDocument,
)
from delivery.domain.enums import DeliveryRequestStatus
from delivery.infrastructure.django.models import DeliveryRequest
from economics.domain.enums import BenchmarkUnit
from economics.infrastructure.django.models import BenchmarkVersion, EconomicBenchmark
from ingestion.domain.enums import (
    DisclaimerAcceptanceMethod,
    ExtractionStrategy,
    FileFormat,
    OcrJobStatus,
    ProcessingStatus,
    SubmissionSource,
)
from ingestion.infrastructure.django.models import ContractSubmission, OcrJob
from platform_core.domain.enums import (
    Band,
    ContractType,
    DeliveryChannel,
    DeliveryStatus,
)
from platform_core.infrastructure.django.models import ContractAnalysis, Project
from rubric.domain.enums import Category
from rubric.infrastructure.django.models import Criterion, RubricVersion

# Deterministic per-test runs: tests that need stable vectors can call
# `random.seed(...)` themselves; the default sequence is good enough for shape checks.
_SHORT_ID_ALPHABET = string.ascii_uppercase + string.digits


def random_vector_384(seed: int | None = None) -> list[float]:
    """Return a list of 384 floats in [-1, 1]. Pass `seed` for reproducibility."""
    rng = random.Random(seed) if seed is not None else random
    return [rng.uniform(-1.0, 1.0) for _ in range(EMBEDDING_DIM)]


def make_public_short_id(year: int | None = None) -> str:
    """Return a string of the form `CS-YYYY-XXXXXX` (6 alphanumeric chars)."""
    year = year or timezone.now().year
    suffix = "".join(secrets.choice(_SHORT_ID_ALPHABET) for _ in range(6))
    return f"CS-{year}-{suffix}"


def age_to(ts: datetime, *, on, field: str = "created_at") -> None:
    """Force a saved row to look like it was created at `ts`.

    `auto_now_add` ignores the provided value at INSERT, so use this to
    backdate after save when testing retention views / cleanup jobs."""
    type(on).objects.filter(pk=on.pk).update(**{field: ts})
    on.refresh_from_db(fields=[field])


def expire_in(delta: timedelta, *, on, field: str = "expires_at") -> None:
    """Set `expires_at` to now()+delta on an already-saved row."""
    new_value = timezone.now() + delta
    type(on).objects.filter(pk=on.pk).update(**{field: new_value})
    on.refresh_from_db(fields=[field])


# ─── Catalog factories (versioned, is_active singletons) ─────────────────────


class RubricVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RubricVersion
        django_get_or_create = ("version",)

    version = factory.Sequence(lambda n: f"1.0.{n}")
    released_at = factory.LazyFunction(timezone.now)
    criteria_count = 38
    categories = factory.LazyFunction(
        lambda: {
            "A": {"weight": 0.15},
            "B": {"weight": 0.20},
            "C": {"weight": 0.15},
            "D": {"weight": 0.15},
            "E": {"weight": 0.20},
            "F": {"weight": 0.15},
        }
    )
    criteria_definitions_path = "rubric/data/rubric_1_0_0.yaml"
    changelog = "Initial test rubric."
    is_active = False


class CriterionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Criterion

    code = factory.Sequence(lambda n: f"A{n + 1}")
    rubric_version = factory.SubFactory(RubricVersionFactory)
    category = Category.A.value
    title = factory.LazyAttribute(lambda o: f"Criterion {o.code} title")
    description = "Test criterion description."
    weight_in_category = Decimal("10.00")
    applicable_types = factory.LazyFunction(lambda: [ContractType.CVP.value, ContractType.ARV.value])
    legal_anchor = factory.LazyFunction(list)
    override_code = None
    evaluation_prompt = "Evaluate the criterion: {{contract_text}}"
    scoring_scale = factory.LazyFunction(lambda: {"10": "perfect", "5": "neutral", "0": "broken"})
    worst_case_when_unverifiable = Decimal("4.0")


class CorpusVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CorpusVersion
        django_get_or_create = ("version",)

    version = factory.Sequence(lambda n: f"2026-test-{n:04d}")
    released_at = factory.LazyFunction(timezone.now)
    laws_count = 1
    articles_count = 10
    chunks_count = 10
    manifest = factory.LazyFunction(lambda: {"laws": ["ley-test"]})
    changelog = ""
    is_active = False


class LegalDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LegalDocument

    law_id = factory.Sequence(lambda n: f"ley-test-{n:03d}")
    corpus_version = factory.SubFactory(CorpusVersionFactory)
    title = factory.LazyAttribute(lambda o: f"Test Law {o.law_id}")
    short_title = ""
    decree = ""
    issued_at = None
    official_gazette = ""
    last_verified = None
    source_url = ""
    status = LegalDocumentStatus.IN_FORCE.value
    subject = "civil"


class LegalChunkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LegalChunk

    id = factory.LazyFunction(lambda: __import__("uuid").uuid4())
    law_id = factory.SelfAttribute("corpus_version.documents.first.law_id")
    corpus_version = factory.SubFactory(CorpusVersionFactory)
    article_number = factory.Sequence(lambda n: f"Art. {n + 1}")
    anchor = factory.Sequence(lambda n: f"art-{n + 1}")
    text_paraphrased = "Paraphrased test chunk."
    text_verbatim = ""
    embedding = factory.LazyFunction(random_vector_384)
    tags = factory.LazyFunction(list)
    relevance_for_findings = factory.LazyFunction(list)
    severity_hint = SeverityHint.YELLOW.value


class BenchmarkVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BenchmarkVersion
        django_get_or_create = ("version",)

    version = factory.Sequence(lambda n: f"2026-Q{(n % 4) + 1}-test-{n}")
    released_at = factory.LazyFunction(timezone.now)
    changelog = ""
    is_active = False


class EconomicBenchmarkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EconomicBenchmark

    benchmark_key = factory.Sequence(lambda n: f"bench_key_{n}")
    benchmark_version = factory.SubFactory(BenchmarkVersionFactory)
    value_min = Decimal("5.0")
    value_max = Decimal("12.0")
    value_default = Decimal("9.0")
    unit = BenchmarkUnit.PCT.value
    applicable_contract_types = factory.LazyFunction(lambda: [ContractType.CVP.value])
    source = "Test source citation"
    source_url = ""
    last_updated = factory.LazyFunction(lambda: timezone.now().date())
    next_review_due = factory.LazyFunction(lambda: (timezone.now() + timedelta(days=90)).date())  # noqa: PLW0108


# ─── Persistent factories (platform_core) ────────────────────────────────────


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Project
        django_get_or_create = ("normalized_name",)

    canonical_name = factory.Sequence(lambda n: f"Test Project {n}")
    normalized_name = factory.Sequence(lambda n: f"test project {n}")
    last_analyzed = factory.LazyFunction(timezone.now)
    total_analyses = 0
    avg_score = None
    score_distribution = factory.LazyFunction(lambda: {"green": 0, "yellow": 0, "red": 0})
    metadata = factory.LazyFunction(dict)
    last_recomputed_at = None


class ContractAnalysisFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContractAnalysis

    public_short_id = factory.LazyFunction(make_public_short_id)
    project = factory.SubFactory(ProjectFactory)
    contract_type = ContractType.CVP.value
    contract_type_declared = None
    contract_type_reclassified = False
    reclassification_reason = ""
    score_total = Decimal("7.5")
    band = Band.YELLOW.value
    override_triggered = factory.LazyFunction(list)
    scores_by_category = factory.LazyFunction(list)
    criterion_evaluations = factory.LazyFunction(list)
    findings = factory.LazyFunction(list)
    findings_count = 0
    critical_findings_count = 0
    unverifiable_count = 0
    economic_summary = None
    rubric_version = factory.SubFactory(RubricVersionFactory)
    corpus_version = factory.SubFactory(CorpusVersionFactory)
    benchmark_version = factory.SubFactory(BenchmarkVersionFactory)
    delivery_status = DeliveryStatus.PENDING.value
    delivery_channel = None
    delivery_target_hash = None
    link_expires_at = None
    resend_count = 0
    anonymized_at = None
    submission_hash = factory.Sequence(lambda n: f"{n:064x}")


# ─── Transient factories ─────────────────────────────────────────────────────


class ContractSubmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ContractSubmission

    submission_hash = factory.Sequence(lambda n: f"{n:064x}")
    file_format = FileFormat.PDF.value
    file_size_bytes = 1024 * 50  # 50 KB
    file_count = 1
    page_count = 4
    source = SubmissionSource.WEB.value
    disclaimer_accepted_at = factory.LazyFunction(timezone.now)
    disclaimer_method = DisclaimerAcceptanceMethod.CHECKBOX.value
    processing_status = ProcessingStatus.RECEIVED.value
    extraction_strategy_attempted = None
    extraction_strategy_successful = None
    extracted_text_token_count = None
    extracted_text_language = None
    error_reason = ""
    error_code = ""
    analysis = None


class OcrJobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OcrJob

    submission = factory.SubFactory(ContractSubmissionFactory)
    strategy = ExtractionStrategy.PYPDF.value
    completed_at = None
    status = OcrJobStatus.RUNNING.value
    error = ""
    error_code = ""
    tokens_consumed = None
    cost_estimate_cents = None
    attempt_number = 1


class DeliveryRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DeliveryRequest

    analysis = factory.SubFactory(ContractAnalysisFactory)
    channel = DeliveryChannel.EMAIL_PDF.value
    target_hash = factory.Sequence(lambda n: f"hash{n:028x}")
    target_value_encrypted = factory.LazyAttribute(lambda o: f"enc::{o.target_hash}")
    delivered_at = None
    attempt_count = 0
    max_attempts = 3
    next_attempt_not_before = None
    status = DeliveryRequestStatus.QUEUED.value
    last_error = ""
    last_error_classification = None


__all__ = [
    "BenchmarkVersionFactory",
    "ContractAnalysisFactory",
    "ContractSubmissionFactory",
    "CorpusVersionFactory",
    "CriterionFactory",
    "DeliveryRequestFactory",
    "EconomicBenchmarkFactory",
    "LegalChunkFactory",
    "LegalDocumentFactory",
    "OcrJobFactory",
    "ProjectFactory",
    "RubricVersionFactory",
    "age_to",
    "expire_in",
    "make_public_short_id",
    "random_vector_384",
]
