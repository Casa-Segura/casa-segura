"""CS-130: benchmark YAML loader + management command coverage.

Test intent (Rule 9): the `version` string in the fixture MUST round-trip into
`BenchmarkVersion.version`; if a future engineer drops that propagation,
PRD_GENERAL BR-13 reproducibility is silently lost. Negative tests pin the
schema contract — invalid `unit`, empty `applicable_contract_types`, inverted
dates — so PRD_F5 §6.3 startup validation cannot be relaxed by accident.
"""

from __future__ import annotations

import textwrap
from decimal import Decimal
from pathlib import Path

import pytest

from django.core.management import CommandError, call_command

from economics.application.benchmark_loader import (
    BenchmarkLoaderError,
    load_yaml,
    upsert_benchmarks,
)
from economics.application.version import latest_active
from economics.infrastructure.django.models import BenchmarkVersion, EconomicBenchmark

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_FIXTURE = REPO_ROOT / "backend" / "fixtures" / "economic_benchmarks_2026q2.yaml"


# ─── Loader unit tests (no DB) ───────────────────────────────────────────────


def _write_yaml(tmp_path: Path, body: str, name: str = "bench.yaml") -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    return path


def test_load_yaml_parses_production_fixture():
    payload = load_yaml(PRODUCTION_FIXTURE)

    assert payload.version == "2026-Q2"
    assert payload.released_at.year == 2026
    assert payload.next_review_due.year == 2026
    assert payload.changelog  # non-empty

    keys = {entry.benchmark_key for entry in payload.entries}
    # PRD_F5 §US-03 minimum list + docs/fixtures/economic-summary/BENCHMARK_KEY_GLOSSARY.md
    # naming convention. Both sources agree on this superset.
    required_minimum = {
        "standard_down_payment_bank_purchase",
        "standard_down_payment_direct_developer_min",
        "standard_down_payment_direct_developer_mid",
        "standard_down_payment_direct_developer_max",
        "bank_mortgage_rate_min",
        "bank_mortgage_rate_mid",
        "bank_mortgage_rate_max",
        "fsv_rate_min",
        "fsv_rate_mid",
        "fsv_rate_max",
        "developer_direct_rate_min",
        "developer_direct_rate_max",
        "credit_term_reasonable_min_months",
        "credit_term_reasonable_max_months",
        "credit_term_ivu_max_months",
        "total_cost_multiplier_healthy_max",
        "total_cost_multiplier_high_max",
        "total_cost_multiplier_excessive_min",
        "monthly_payment_ratio_healthy_max",
        "monthly_payment_ratio_high_max",
        "monthly_payment_ratio_excessive_min",
    }
    missing = required_minimum - keys
    assert not missing, f"PRD_F5 US-03 / glossary minimum list missing: {sorted(missing)}"


def test_load_yaml_rejects_unknown_unit(tmp_path: Path):
    path = _write_yaml(
        tmp_path,
        """
        version: "test"
        released_at: "2026-01-01"
        next_review_due: "2026-04-01"
        benchmarks:
          some_key:
            value_default: 0.10
            unit: parsecs
            applicable_contract_types: [CVC]
            source: "test"
            last_updated: 2026-01-01
            next_review_due: 2026-04-01
        """,
    )
    with pytest.raises(BenchmarkLoaderError, match="unit 'parsecs' not in"):
        load_yaml(path)


def test_load_yaml_rejects_empty_applicable_contract_types(tmp_path: Path):
    path = _write_yaml(
        tmp_path,
        """
        version: "test"
        released_at: "2026-01-01"
        next_review_due: "2026-04-01"
        benchmarks:
          some_key:
            value_default: 0.10
            unit: pct
            applicable_contract_types: []
            source: "test"
            last_updated: 2026-01-01
            next_review_due: 2026-04-01
        """,
    )
    with pytest.raises(BenchmarkLoaderError, match="applicable_contract_types must be a non-empty list"):
        load_yaml(path)


def test_load_yaml_rejects_inverted_review_window(tmp_path: Path):
    path = _write_yaml(
        tmp_path,
        """
        version: "test"
        released_at: "2026-01-01"
        next_review_due: "2026-04-01"
        benchmarks:
          some_key:
            value_default: 0.10
            unit: pct
            applicable_contract_types: [CVC]
            source: "test"
            last_updated: 2026-06-01
            next_review_due: 2026-04-01
        """,
    )
    with pytest.raises(BenchmarkLoaderError, match=r"next_review_due .* before last_updated"):
        load_yaml(path)


def test_load_yaml_rejects_missing_top_level(tmp_path: Path):
    path = _write_yaml(
        tmp_path,
        """
        version: "test"
        benchmarks: {}
        """,
    )
    with pytest.raises(BenchmarkLoaderError, match="missing required top-level keys"):
        load_yaml(path)


def test_load_yaml_rejects_negative_value(tmp_path: Path):
    path = _write_yaml(
        tmp_path,
        """
        version: "test"
        released_at: "2026-01-01"
        next_review_due: "2026-04-01"
        benchmarks:
          some_key:
            value_default: -0.05
            unit: pct
            applicable_contract_types: [CVC]
            source: "test"
            last_updated: 2026-01-01
            next_review_due: 2026-04-01
        """,
    )
    with pytest.raises(BenchmarkLoaderError, match="value_default must be >= 0"):
        load_yaml(path)


def test_load_yaml_rejects_inverted_min_max(tmp_path: Path):
    path = _write_yaml(
        tmp_path,
        """
        version: "test"
        released_at: "2026-01-01"
        next_review_due: "2026-04-01"
        benchmarks:
          some_key:
            value_min: 0.20
            value_max: 0.10
            unit: pct
            applicable_contract_types: [CVC]
            source: "test"
            last_updated: 2026-01-01
            next_review_due: 2026-04-01
        """,
    )
    with pytest.raises(BenchmarkLoaderError, match=r"value_min .* > value_max"):
        load_yaml(path)


def test_load_yaml_rejects_malformed_yaml(tmp_path: Path):
    path = _write_yaml(
        tmp_path,
        """
        version: "test
        """,
    )
    with pytest.raises(BenchmarkLoaderError, match="Invalid YAML"):
        load_yaml(path)


# ─── DB upsert + management command (with DB) ────────────────────────────────


@pytest.mark.django_db
def test_upsert_benchmarks_persists_version_and_rows():
    payload = load_yaml(PRODUCTION_FIXTURE)
    version_obj, created, updated = upsert_benchmarks(payload, activate=False)

    assert version_obj.version == "2026-Q2"
    assert created == len(payload.entries)
    assert updated == 0
    assert EconomicBenchmark.objects.filter(benchmark_version=version_obj).count() == len(payload.entries)


@pytest.mark.django_db
def test_upsert_benchmarks_idempotent_second_run():
    payload = load_yaml(PRODUCTION_FIXTURE)
    upsert_benchmarks(payload, activate=False)
    _, created, updated = upsert_benchmarks(payload, activate=False)

    assert created == 0
    assert updated == len(payload.entries)


@pytest.mark.django_db
def test_upsert_benchmarks_activates_singleton():
    """Rule 9 — `version` propagation: fixture version IS the active version string."""

    payload = load_yaml(PRODUCTION_FIXTURE)
    version_obj, *_ = upsert_benchmarks(payload, activate=True)

    assert version_obj.is_active is True
    active = latest_active()
    assert active is not None
    # Byte-equal version echo — CS-136 will reuse this guarantee.
    assert active.version == "2026-Q2" == payload.version


@pytest.mark.django_db
def test_load_benchmark_catalog_command_loads_and_activates():
    call_command(
        "load_benchmark_catalog",
        f"--fixture={PRODUCTION_FIXTURE}",
        "--benchmark-version=2026-Q2",
        "--activate",
    )
    active = latest_active()
    assert active is not None
    assert active.version == "2026-Q2"
    bench = EconomicBenchmark.objects.get(benchmark_key="bank_mortgage_rate_mid", benchmark_version=active)
    assert bench.value_default == Decimal("0.0800")
    assert bench.unit == "pct"
    assert "CVC" in bench.applicable_contract_types


@pytest.mark.django_db
def test_load_benchmark_catalog_command_rejects_mismatched_version():
    with pytest.raises(CommandError, match="fixture version is '2026-Q2'"):
        call_command(
            "load_benchmark_catalog",
            f"--fixture={PRODUCTION_FIXTURE}",
            "--benchmark-version=1999-Q4",
        )


@pytest.mark.django_db
def test_seed_benchmark_version_command_creates_row():
    call_command("seed_benchmark_version", "--benchmark-version=2026-Q3", "--activate")
    obj = BenchmarkVersion.objects.get(version="2026-Q3")
    assert obj.is_active is True
