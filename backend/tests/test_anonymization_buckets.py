"""Unit tests for PRD F8 US-08 bucketing (CS-273 BVA) — no DB."""

from __future__ import annotations

from decimal import Decimal

import pytest

from platform_core.worker.retention import anonymization


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        (Decimal("29999"), "<30k"),
        (Decimal("30000"), "30k-60k"),
        (Decimal("59999"), "30k-60k"),
        (Decimal("60000"), "60k-100k"),
        (Decimal("99999"), "60k-100k"),
        (Decimal("100000"), "100k-150k"),
        (Decimal("149999"), "100k-150k"),
        (Decimal("150000"), "150k-250k"),
        (Decimal("249999"), "150k-250k"),
        (Decimal("250000"), ">250k"),
    ],
)
def test_bucket_price_cash_edges(price: Decimal, expected: str) -> None:
    raw = {
        "fields_extracted": {"price_cash": str(price)},
        "benchmark_comparisons": (),
        "benchmark_version": "v-test",
        "contract_type": "CVP",
    }
    out = anonymization.anonymize_economic_summary(raw)
    assert out is not None
    assert out["price_cash_bucket"] == expected


def test_bucket_down_payment_pct_five_stays_low_band() -> None:
    raw = {
        "fields_extracted": {"down_payment_pct": "5.0"},
        "benchmark_comparisons": (),
        "benchmark_version": "v-test",
        "contract_type": "CVP",
    }
    assert anonymization.anonymize_economic_summary(raw)["down_payment_pct_bucket"] == "0-5"


@pytest.mark.parametrize(
    ("rate", "expected"),
    [
        (Decimal("6.99"), "<7"),
        (Decimal("7"), "7-9"),
        (Decimal("8.99"), "7-9"),
        (Decimal("9"), "9-12"),
        (Decimal("11.99"), "9-12"),
        (Decimal("12"), "12-15"),
        (Decimal("14.99"), "12-15"),
        (Decimal("15"), "15-20"),
        (Decimal("19.99"), "15-20"),
        (Decimal("20"), ">20"),
    ],
)
def test_bucket_annual_rate_edges(rate: Decimal, expected: str) -> None:
    raw = {
        "fields_extracted": {"annual_rate_pct": str(rate)},
        "benchmark_comparisons": (),
        "benchmark_version": "v-test",
        "contract_type": "CVP",
    }
    assert anonymization.anonymize_economic_summary(raw)["annual_rate_pct_bucket"] == expected


@pytest.mark.parametrize(
    ("months", "expected"),
    [
        (119, "<120"),
        (120, "120-180"),
        (179, "120-180"),
        (180, "180-240"),
        (239, "180-240"),
        (240, "240-300"),
        (299, "240-300"),
        (300, ">300"),
    ],
)
def test_bucket_term_months_edges(months: int, expected: str) -> None:
    raw = {
        "fields_extracted": {"term_months": months},
        "benchmark_comparisons": (),
        "benchmark_version": "v-test",
        "contract_type": "CVP",
    }
    assert anonymization.anonymize_economic_summary(raw)["term_months_bucket"] == expected


def test_reduce_scores_by_category_strips_detail() -> None:
    rows = [
        {
            "category": "A",
            "score": 8.0,
            "category_name": "Legal",
            "weight_global": 0.2,
        }
    ]
    assert anonymization.reduce_scores_by_category(rows) == [{"category": "A", "score": 8.0}]


def test_benchmark_rows_scrubbed() -> None:
    raw = {
        "fields_extracted": {},
        "benchmark_comparisons": [
            {
                "metric": "rate",
                "assessment": "high",
                "contract_value": "10",
                "benchmark_value": "9",
            }
        ],
        "benchmark_version": "v-test",
        "contract_type": "CVP",
    }
    out = anonymization.anonymize_economic_summary(raw)
    assert out["benchmark_comparisons"] == [{"metric": "rate", "assessment": "high"}]


def test_overcost_bucket_thresholds() -> None:
    raw_base = {
        "fields_extracted": {},
        "benchmark_comparisons": (),
        "benchmark_version": "v-test",
        "contract_type": "CVP",
        "overcost": {"vs_benchmark_usd": "0", "explanation": "x", "what_changes_would_save": []},
    }
    assert anonymization.anonymize_economic_summary(raw_base)["overcost_label"] == "none"
    raw_small = {
        **raw_base,
        "overcost": {"vs_benchmark_usd": "1000", "explanation": "x", "what_changes_would_save": []},
    }
    assert anonymization.anonymize_economic_summary(raw_small)["overcost_label"] == "small"
    raw_med = {
        **raw_base,
        "overcost": {"vs_benchmark_usd": "10000", "explanation": "x", "what_changes_would_save": []},
    }
    assert anonymization.anonymize_economic_summary(raw_med)["overcost_label"] == "medium"
    raw_large = {
        **raw_base,
        "overcost": {"vs_benchmark_usd": "30000", "explanation": "x", "what_changes_would_save": []},
    }
    assert anonymization.anonymize_economic_summary(raw_large)["overcost_label"] == "large"
