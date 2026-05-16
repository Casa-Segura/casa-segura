"""Economic catalog — BenchmarkVersion + EconomicBenchmark.

DOMAIN_MODEL §3.8 + F8 extension. Versioned catalog of market benchmarks
(rates, fees, valuation multipliers, etc.) used by F5."""

from __future__ import annotations

from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from django.db import models
from django.db.models import Q

from common.infrastructure.django.models import ModelWithTimeStamps
from economics.domain.enums import BenchmarkUnit


class BenchmarkVersion(ModelWithTimeStamps):
    """Version of the economic benchmark catalog. Immutable; only `is_active` may flip."""

    version = models.CharField(
        max_length=32,
        primary_key=True,
        help_text="Semver or date-based version, e.g. 2026-Q2",
    )
    released_at = models.DateTimeField(help_text="When this benchmark version was published")
    changelog = models.TextField(blank=True, default="", help_text="Summary of changes vs prior version")
    is_active = models.BooleanField(
        default=False,
        help_text="Exactly one benchmark version may be active at a time",
    )

    class Meta:
        db_table = "benchmark_version"
        verbose_name = "Benchmark Version"
        verbose_name_plural = "Benchmark Versions"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="uq_benchmark_version_active_singleton",
            ),
        ]

    def __str__(self) -> str:
        return f"BenchmarkVersion({self.version})"


class EconomicBenchmark(ModelWithTimeStamps):
    """Market benchmark used in economic calculations. DOMAIN §3.8.

    Composite uniqueness `(benchmark_key, benchmark_version)`; same key may
    appear in multiple versions with different values."""

    benchmark_key = models.CharField(
        max_length=64,
        help_text="Stable key, e.g. 'bank_mortgage_rate_max'",
    )
    benchmark_version = models.ForeignKey(
        BenchmarkVersion,
        on_delete=models.PROTECT,
        related_name="benchmarks",
        db_column="benchmark_version",
        help_text="Version this benchmark belongs to",
    )
    value_min = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True, help_text="Lower bound (nullable)"
    )
    value_max = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True, help_text="Upper bound (nullable)"
    )
    value_default = models.DecimalField(
        max_digits=18, decimal_places=4, null=True, blank=True, help_text="Recommended single value (nullable)"
    )
    unit = models.CharField(
        max_length=16,
        choices=BenchmarkUnit.choices,
        help_text="Unit of the value (pct, usd, months, multiplier, ratio)",
    )
    applicable_contract_types = ArrayField(
        models.CharField(max_length=16),
        help_text="Contract types this benchmark applies to",
    )
    source = models.TextField(help_text="Source citation (e.g. BCR table, SSF circular)")
    source_url = models.URLField(max_length=512, blank=True, default="", help_text="URL of the source")
    last_updated = models.DateField(help_text="When the underlying market figure was last refreshed")
    next_review_due = models.DateField(help_text="When the next benchmark review is scheduled")

    class Meta:
        db_table = "economic_benchmark"
        verbose_name = "Economic Benchmark"
        verbose_name_plural = "Economic Benchmarks"
        constraints = [
            models.UniqueConstraint(
                fields=["benchmark_key", "benchmark_version"],
                name="uq_economic_benchmark_key_version",
            ),
            models.CheckConstraint(
                check=Q(unit__in=[u.value for u in BenchmarkUnit]),
                name="ck_economic_benchmark_unit_enum",
            ),
        ]
        indexes = [
            models.Index(fields=["benchmark_version"], name="idx_economic_benchmark_version"),
            GinIndex(fields=["applicable_contract_types"], name="idx_economic_benchmark_types"),
        ]

    def __str__(self) -> str:
        return f"EconomicBenchmark({self.benchmark_key}@{self.benchmark_version_id})"
