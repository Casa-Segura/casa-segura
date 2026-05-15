# Implementation Plan — F5: Economic Analysis & Benchmarks

> Generated: 2026-05-15
> Stack: Django 5.2 LTS + Celery + Postgres (no LLM)
> Module: `economics/`
> Depends: F2 (raw fields), F8 (schema), uses F4's barrier indirectly

---

## Directory Structure

```
economics/
├── domain/
│   ├── entities.py           # EconomicSummary, ExtractedFields, DerivedFields, BenchmarkComparison, Overcost, EconomicWarning, BenchmarkVersion, EconomicBenchmark
│   ├── enums.py              # BenchmarkUnit, Assessment, WarningCode
│   └── exceptions.py
├── application/
│   ├── commands.py           # ComputeEconomicSummary, LoadBenchmarks, ActivateBenchmarks, PersistEconomicSummary
│   ├── queries.py            # GetActiveBenchmarkVersion, GetBenchmarksFor, GetBenchmarkByKey
│   ├── handlers/
│   │   └── economic_handlers.py
│   └── services/
│       ├── economic_analysis_service.py
│       ├── french_amortization.py
│       └── currency_converter.py
└── infrastructure/
    ├── django/
    │   ├── apps.py
    │   ├── models.py         # BenchmarkVersionModel, EconomicBenchmarkModel
    │   ├── repositories.py
    │   ├── serializers.py
    │   ├── views.py          # InternalAnalyzeView, InternalBenchmarksView
    │   ├── urls.py
    │   ├── management/commands/
    │   │   ├── benchmarks_load.py
    │   │   └── benchmarks_activate.py
    │   └── migrations/
    │       └── 0001_initial.py
    ├── celery/
    │   └── economic_tasks.py # @shared_task compute_summary
    ├── benchmarks/
    │   └── 2026-Q2.yaml      # versioned benchmark file
    └── redis/
        └── stream_consumer.py
```

---

## App Configuration

```python
# economics/infrastructure/django/apps.py
from django.apps import AppConfig

class EconomicsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "economics.infrastructure.django"
    label = "economics"
    verbose_name = "Casa Segura — Economic Analysis"
```

`INSTALLED_APPS` includes `"economics.infrastructure.django"`; migrations under `economics/infrastructure/django/migrations/`; URLs under `/v1/internal/economic/`.

---

## Domain Entities (Pydantic)

(Already detailed in `ENTITY_RELATIONSHIP_DIAGRAM.md`.)

## Enumerations

```python
# economics/domain/enums.py
from django.db import models

class BenchmarkUnit(models.TextChoices):
    PCT = "pct"
    USD = "usd"
    MONTHS = "months"
    MULTIPLIER = "multiplier"
    RATIO = "ratio"

class Assessment(models.TextChoices):
    BELOW_MARKET_FAVORABLE = "below_market_favorable"
    WITHIN_MARKET = "within_market"
    SLIGHTLY_ABOVE_MARKET = "slightly_above_market"
    ABOVE_MARKET = "above_market"
    WELL_ABOVE_MARKET = "well_above_market"

class WarningCode(models.TextChoices):
    MONTHLY_PAYMENT_HIGHER_THAN_THEORETICAL = "monthly_payment_higher_than_theoretical"
    DOWN_PAYMENT_INCONSISTENT = "down_payment_inconsistent"
    INTEREST_CALCULATION_BASE_UNFAVORABLE = "interest_calculation_base_unfavorable"
    TOTAL_COST_NOT_DISCLOSED = "total_cost_not_disclosed"
    ANNUAL_RATE_NOT_EXPRESSED = "annual_rate_not_expressed"
    TERM_EXCESSIVE = "term_excessive"
```

## Commands and Queries

```python
# economics/application/commands.py
from uuid import UUID
from pydantic import BaseModel
from classification.domain.entities import EconomicFieldsRaw
from classification.domain.enums import ContractType


class ComputeEconomicSummary(BaseModel):
    analysis_id: UUID
    raw_fields: EconomicFieldsRaw
    contract_type: ContractType


class LoadBenchmarks(BaseModel):
    version: str
    path: str
    force: bool = False


class ActivateBenchmarks(BaseModel):
    version: str
```

```python
# economics/application/queries.py
from shared.domain.entities.cqrs import BaseGetAttributes, BaseFilterAttributes, Query


class GetActiveBenchmarkVersion(BaseGetAttributes, Query): pass

class GetBenchmarksFor(BaseFilterAttributes, Query):
    benchmark_version: str
    contract_type: str

class GetBenchmarkByKey(BaseGetAttributes, Query):
    benchmark_key: str
    benchmark_version: str
```

## New Dependencies

- `pyyaml` ≥ 6.0 (already added by F3)
- No new packages

---

## Story: US-01 — Normalize and validate raw fields

`EconomicAnalysisService.normalize(raw) -> ExtractedFields`. Tests for: SVC→USD, %, term in months, rate out-of-range marked invalid.

## Story: US-02 — Derive fields

`EconomicAnalysisService.derive(extracted)` plus `FrenchAmortization.monthly_payment(financed, annual_rate, term_months)`. Tests for: coherence cross-check 5%; theoretical monthly when monthly_payment missing.

## Story: US-03 — Load versioned benchmarks

`BenchmarkLoader.load_yaml + validate`. Management command `benchmarks_load`. Tests for: required fields, date ordering, duplicates rejected.

## Story: US-04 — Build BenchmarkComparison

`EconomicAnalysisService.compare(extracted, derived, benchmarks, contract_type)`. Per-metric assessment with asymmetric rule. Tests for: rate -1pp → below_market_favorable; +1pp → slightly_above; +5pp → well_above.

## Story: US-05 — Compute overcost

`EconomicAnalysisService.compute_overcost` substitutes rate only (asymmetric); uses FrenchAmortization. Tests for: rate above max → substituted; rate below min → no substitution; no overcost ≤ 0 returns None.

## Story: US-06 — Emit warnings

Inline in service; tested per WarningCode.

## Story: US-07 — Persist EconomicSummary

`ContractAnalysisRepository.persist_economic_summary(analysis_id, summary, benchmark_version)`: single UPDATE.

### Reference Code (selected)

```python
# economics/application/services/french_amortization.py

class FrenchAmortization:
    @staticmethod
    def monthly_payment(financed: float, annual_rate: float, term_months: int) -> float:
        if annual_rate == 0:
            return financed / term_months
        r = annual_rate / 12
        n = term_months
        return financed * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    @staticmethod
    def total_cost(financed: float, monthly: float, term_months: int, down: float = 0.0) -> float:
        return down + monthly * term_months
```

```python
# economics/application/services/currency_converter.py

USD_PER_SVC = 1 / 8.75  # fixed historical parity

class CurrencyConverter:
    @staticmethod
    def to_usd(value: float, currency: str) -> tuple[float, str | None]:
        if currency is None or currency.upper() == "USD":
            return value, None
        if currency.upper() in {"SVC", "COLON", "COLONES", "₡", "¢"}:
            return value * USD_PER_SVC, f"converted from SVC at fixed parity 8.75 SVC/USD"
        raise ValueError(f"Unsupported currency: {currency}")
```

```python
# economics/application/services/economic_analysis_service.py (excerpt)

class EconomicAnalysisService:
    def __init__(self, *, benchmark_repository, benchmark_version_repository, analysis_repository, currency_converter=None, amortization=None):
        self.benchmark_repository = benchmark_repository
        self.benchmark_version_repository = benchmark_version_repository
        self.analysis_repository = analysis_repository
        self.currency_converter = currency_converter or CurrencyConverter()
        self.amortization = amortization or FrenchAmortization()

    def compute(self, *, analysis_id: UUID, raw: EconomicFieldsRaw, contract_type: ContractType) -> EconomicSummary:
        version = self.benchmark_version_repository.get_active()
        benchmarks = self.benchmark_repository.list_for(version.version, contract_type)

        # Early exit for cash / minimal contracts
        if contract_type in (ContractType.CVC, ContractType.ARC, ContractType.IVU):
            return self._minimal_summary(raw, contract_type, version.version)

        extracted = self.normalize(raw)
        derived = self.derive(extracted)
        comparisons = self.compare(extracted, derived, benchmarks, contract_type)
        overcost = self.compute_overcost(extracted, derived, benchmarks, contract_type)
        warnings = self.emit_warnings(raw, extracted, derived, comparisons)

        return EconomicSummary(
            contract_type=contract_type,
            currency="USD",
            currency_conversion_note=extracted.currency_conversion_note,
            fields_extracted=extracted.to_simple(),
            fields_derived=derived,
            benchmark_comparisons=comparisons,
            overcost=overcost,
            warnings=warnings,
            benchmark_version=version.version,
            derivation_status="ok" if extracted.has_any() else "insufficient_data",
        )
```

---

## Part 2 — Staged Execution Plan

### Codebase Alignment Rules

- Django 5.2 LTS, DRF only for internal endpoints
- `EconomicBenchmarkModel`, `BenchmarkVersionModel` declared in `economics/infrastructure/django/models.py` (catalog tables; F8 doesn't own them)
- Celery task `economics.compute_summary`
- All env vars under `F5_*` or `BENCHMARK_*`

### Stage Overview

| # | Stage | Deliverable |
|---|---|---|
| 1 | Domain entities/enums/exceptions | Pydantic + TextChoices |
| 2 | Commands/queries | CQRS |
| 3 | Handlers | Plain functions |
| 4 | Service + adapters | FrenchAmortization, CurrencyConverter, EconomicAnalysisService |
| 5 | Django models + initial migration | BenchmarkVersionModel, EconomicBenchmarkModel |
| 6 | Benchmark YAML + seed migration | `economics/benchmarks/2026-Q2.yaml` + `0002_seed_2026_Q2.py` |
| 7 | Repositories | BenchmarkRepository, BenchmarkVersionRepository, augment ContractAnalysisRepository |
| 8 | Mgmt commands | benchmarks_load, benchmarks_activate |
| 9 | Celery task | compute_summary |
| 10 | Stream consumer daemon | XREADGROUP from classification.to_rubric_and_economics group economics |
| 11 | Internal endpoints | InternalAnalyzeView, InternalBenchmarksView |
| 12 | Tests | unit + integration |
| 13 | Observability | Prometheus metrics |

### Stage 5: Django models

```python
# economics/infrastructure/django/models.py
from django.contrib.postgres.fields import ArrayField
from django.db import models
from economics.domain.enums import BenchmarkUnit


class BenchmarkVersionModel(models.Model):
    version = models.TextField(primary_key=True, help_text="Benchmark version tag, e.g. 2026-Q2.")
    released_at = models.DateTimeField(auto_now_add=True, help_text="Publication time.")
    benchmark_count = models.IntegerField(help_text="Number of benchmark rows in this version.")
    changelog = models.TextField(null=True, blank=True, help_text="Notes vs prior version.")
    is_active = models.BooleanField(default=False, help_text="Whether this is the version new analyses use.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created timestamp.")

    class Meta:
        db_table = "benchmark_version"

    def __str__(self) -> str:
        return f"BenchmarkVersion {self.version}"


class EconomicBenchmarkModel(models.Model):
    benchmark_key = models.TextField(help_text="Stable key, e.g. bank_mortgage_rate_mid.")
    benchmark_version = models.ForeignKey(BenchmarkVersionModel, on_delete=models.PROTECT, related_name="benchmarks", help_text="Owning version.")
    value_min = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Lower bound of range, if applicable.")
    value_max = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Upper bound of range, if applicable.")
    value_default = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True, help_text="Single canonical value.")
    unit = models.CharField(max_length=16, choices=BenchmarkUnit.choices, help_text="pct/usd/months/multiplier/ratio.")
    applicable_contract_types = ArrayField(models.CharField(max_length=16), help_text="Contract types this benchmark applies to.")
    source = models.TextField(help_text="Cited source.")
    source_url = models.TextField(null=True, blank=True, help_text="URL to the official source.")
    last_updated = models.DateField(help_text="Last update date of this benchmark value.")
    next_review_due = models.DateField(help_text="When the value should be re-verified.")
    notes = models.TextField(null=True, blank=True, help_text="Editorial notes.")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Created timestamp.")

    class Meta:
        db_table = "economic_benchmark"
        unique_together = [("benchmark_key", "benchmark_version")]
        indexes = [
            models.Index(fields=["benchmark_version"], name="idx_benchmark_version"),
        ]

    def __str__(self) -> str:
        return f"EconomicBenchmark {self.benchmark_key} ({self.benchmark_version})"
```

### Stage 9 — Celery task

```python
# economics/infrastructure/celery/economic_tasks.py
from celery import shared_task
import json

@shared_task(name="economics.compute_summary", bind=True, max_retries=2)
def compute_summary(self, analysis_id: str, raw_fields_json: str, contract_type: str) -> None:
    from economics.application.services.economic_analysis_service import EconomicAnalysisService
    service = EconomicAnalysisService(...)
    raw = EconomicFieldsRaw.model_validate_json(raw_fields_json) if raw_fields_json else None
    summary = service.compute(analysis_id=UUID(analysis_id), raw=raw or EconomicFieldsRaw(), contract_type=ContractType(contract_type))
    service.analysis_repository.persist_economic_summary(UUID(analysis_id), summary, summary.benchmark_version)
```

### Stage 13 — Metrics

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `f5_compute_latency_seconds` | Histogram | — | P50/P95 |
| `f5_assessment_total` | Counter | `metric`, `assessment` | Distribution per metric |
| `f5_warning_total` | Counter | `warning_code` | Frequency |
| `f5_insufficient_data_total` | Counter | — | How often we hit insufficient |
| `f5_benchmark_age_days` | Gauge | `version` | Age tracking |
| `f5_overcost_usd` | Histogram | — | Distribution of overcost |

---

## Error Codes

| Code | Description |
|---|---|
| `INVALID_BENCHMARK_FILE` | YAML malformed |
| `BENCHMARK_VERSION_EXISTS` | Version already present, no --force |
| `BENCHMARK_RANGE_INVALID` | Value out of plausible bounds |
| `CURRENCY_NOT_SUPPORTED` | Currency neither USD nor SVC |
| `BENCHMARKS_EXPIRED` | Operational alert (warning) when `next_review_due < today` |

---

## Configuration matrix

| Variable | Default | Purpose |
|---|---|---|
| `BENCHMARK_FILE_PATH` | `economics/benchmarks/2026-Q2.yaml` | Default load path |
| `BENCHMARK_RELOAD_ON_SIGHUP` | `false` | Optional hot reload |
| `EXCHANGE_RATE_USD_PER_SVC` | `0.114285714` (= 1/8.75) | Fixed parity |
| `BENCHMARK_EXPIRED_ALERT_DAYS` | 30 | Alert lead time |
| `ECONOMIC_STREAM_GROUP` | `economics` | Consumer group |
| `ECONOMIC_STREAM_NAME_IN` | `classification.to_rubric_and_economics` | F2→F5 |
| `F5_COHERENCE_TOLERANCE` | 0.05 | 5% |

---

**End of document.**
