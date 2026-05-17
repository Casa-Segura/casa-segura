"""CS-136: benchmark_version stamping + freshness alert coverage.

Test intent (Rule 9): `test_benchmark_version_is_provenance_distinct_from_rubric`
ensures the persisted `economic_summary.benchmark_version` carries the
catalog's tag — not the rubric version. If a future engineer accidentally
stamps `rubric_version` into the benchmark slot the test fails.

PRD_GENERAL BR-13: reproducibility requires the exact catalog tag stamped on
every analysis.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

import pytest
import structlog

from django.utils import timezone

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.contract_type import ContractType
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.application.analyzer import analyze
from economics.application.benchmark_loader import load_yaml, upsert_benchmarks
from economics.application.catalog import BenchmarkCatalog
from economics.application.version import assert_freshness, latest_active
from economics.infrastructure.django.models import EconomicBenchmark
from shared.observability.logging import _add_default_versions

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_FIXTURE = REPO_ROOT / "backend" / "fixtures" / "economic_benchmarks_2026q2.yaml"


def _slot(name: str, value, status=ExtractionStatus.PRESENT) -> EconomicSlot:
    return EconomicSlot(field_name=name, status=status, value=value, confidence=0.9)


@pytest.fixture
def loaded_catalog(db) -> BenchmarkCatalog:
    payload = load_yaml(PRODUCTION_FIXTURE)
    version_obj, *_ = upsert_benchmarks(payload, activate=True)
    return BenchmarkCatalog.from_db(version_obj)


# ─── Logging contract ────────────────────────────────────────────────────────


def test_default_versions_processor_emits_benchmark_version_key():
    """structlog processor must always emit `benchmark_version` (default None)."""

    out = _add_default_versions(None, "info", {})

    assert "benchmark_version" in out
    assert out["benchmark_version"] is None
    # Sibling keys still present.
    assert out["rubric_version"] is None
    assert out["corpus_version"] is None


# ─── Stamp parity (Rule 9 anchor) ────────────────────────────────────────────


@pytest.mark.django_db
def test_summary_benchmark_version_echoes_catalog_byte_equal(loaded_catalog):
    extraction = AggregatedExtraction(
        contract_type=ContractType.CVP,
        slots={
            "purchase_price_usd": _slot("purchase_price_usd", 80_000),
            "down_payment_usd": _slot("down_payment_usd", 8_000),
            "financed_amount_usd": _slot("financed_amount_usd", 72_000),
            "term_months": _slot("term_months", 240),
            "interest_rate_pct": _slot("interest_rate_pct", 0.18),
            "monthly_payment_usd": _slot("monthly_payment_usd", 1083.50),
        },
    )

    summary = analyze(extraction, catalog=loaded_catalog)
    active = latest_active()

    # PRD_GENERAL BR-13: persisted JSON's benchmark_version is byte-for-byte
    # identical to the active BenchmarkVersion.version column.
    assert summary.benchmark_version == "2026-Q2"
    assert active is not None
    assert summary.benchmark_version == active.version


@pytest.mark.django_db
def test_benchmark_version_is_provenance_distinct_from_rubric(loaded_catalog):
    """Rule 9 — distinct provenance: benchmark version is NOT a rubric version.

    DOMAIN_MODEL §3.2 lists `rubric_version`, `corpus_version`, and
    `benchmark_version` as three independent version columns on
    `ContractAnalysis`. This test pins that the assembler stamps the
    catalog's string, not anything sourced from the rubric.
    """

    extraction = AggregatedExtraction(
        contract_type=ContractType.CVP,
        slots={
            "purchase_price_usd": _slot("purchase_price_usd", 80_000),
            "down_payment_usd": _slot("down_payment_usd", 8_000),
            "financed_amount_usd": _slot("financed_amount_usd", 72_000),
            "term_months": _slot("term_months", 240),
            "interest_rate_pct": _slot("interest_rate_pct", 0.09),
            "monthly_payment_usd": _slot("monthly_payment_usd", 700.0),
        },
    )

    summary = analyze(extraction, catalog=loaded_catalog)

    # Sanity: the rubric uses `1.0.0` semver style; the benchmark catalog
    # uses date-quarter strings (`2026-Q2`). They MUST NOT collide today —
    # if a future engineer swaps the slot the format mismatch fails this
    # assertion loudly.
    assert summary.benchmark_version == "2026-Q2"
    assert not summary.benchmark_version.startswith("1.")  # not a rubric semver
    assert "-Q" in summary.benchmark_version  # date-quarter shape


# ─── Freshness signal ────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_freshness_warning_when_next_review_due_in_past(loaded_catalog, caplog):
    """BR-12 — expired benchmarks emit operational alert without blocking analysis."""

    # Backdate every benchmark's `next_review_due` to yesterday.
    yesterday = timezone.now().date() - timedelta(days=1)
    EconomicBenchmark.objects.filter(benchmark_version=latest_active()).update(next_review_due=yesterday)

    # Capture structlog log records via the stdlib logging integration.
    structlog.reset_defaults()
    structlog.configure(
        processors=[structlog.stdlib.add_log_level, structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    with caplog.at_level(logging.WARNING, logger="economics.application.version"):
        assert_freshness(latest_active())

    assert any("benchmark.version.stale" in rec.message for rec in caplog.records)


@pytest.mark.django_db
def test_freshness_silent_when_within_window(loaded_catalog, caplog):
    """Catalog inside its review window must NOT emit a stale warning."""

    with caplog.at_level(logging.WARNING, logger="economics.application.version"):
        assert_freshness(latest_active())

    assert not any("benchmark.version.stale" in rec.message for rec in caplog.records)


def test_assert_freshness_silent_on_none():
    """Defensive: `None` version (no active catalog) is a no-op, not a crash."""

    # Should return cleanly without raising.
    assert_freshness(None)
