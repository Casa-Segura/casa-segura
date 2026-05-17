"""Benchmark comparison + overcost DTOs — CS-134.

Mirrors the `BenchmarkComparison` and `overcost` rows from
`docs/analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md` (the
cross-team normative contract for `economic_summary.benchmark_comparisons`
and `economic_summary.overcost`).

`BenchmarkSegment` is internal — the comparator uses it to pick which range
of benchmark keys applies per BR-10 / BR-11; it does not surface in the
persisted JSON.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class BenchmarkSegment(StrEnum):
    """Per-contract benchmark band selection per BR-10 / BR-11."""

    BANK_PURCHASE = "bank_purchase"
    DEVELOPER_DIRECT = "developer_direct"
    FSV = "fsv"


class BenchmarkComparison(BaseModel):
    """One contract-vs-benchmark row.

    `assessment` values match the persisted DOMAIN_MODEL §5.6 enum (4
    bands) — the wider PRD_F5 US-04 5-band scale is collapsed to the
    catalog-aligned shape per `ECONOMIC_SUMMARY_CONTRACT.md`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str = Field(min_length=1, max_length=64)
    metric_label: str = Field(min_length=1, max_length=128)
    contract_value: Decimal
    benchmark_value: Decimal
    benchmark_key: str = Field(min_length=1, max_length=64)
    benchmark_source: str = Field(min_length=1)
    delta_pct_points: Decimal | None = Field(default=None)
    assessment: str = Field(min_length=1, max_length=32)


class Overcost(BaseModel):
    """Estimated overpayment vs the segment-matched benchmark scenario.

    Per PRD_F5 US-05 + ECONOMIC_SUMMARY_CONTRACT: `null` when not applicable
    (e.g. FSV inside its band per BR-11, or below market per BR-02).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    vs_benchmark_usd: Decimal
    explanation: str = Field(min_length=1, max_length=2000)
    what_changes_would_save: tuple[str, ...] = Field(default=())


__all__ = ["BenchmarkComparison", "BenchmarkSegment", "Overcost"]
