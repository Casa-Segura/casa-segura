"""EconomicSummary contract DTOs — CS-135.

Pydantic v2 models for the persisted `ContractAnalysis.economic_summary`
JSONB shape per `docs/analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md`.

Authority order when sources disagree:
    1. PRD_F5 US-07 (nested `fields_extracted` / `fields_derived`,
       `overcost`, `warnings`, `benchmark_version`).
    2. ECONOMIC_SUMMARY_CONTRACT.md (this commit's source of truth for
       `derivation_status`, `severity_suggested` literal, dedupe rule).
    3. DOMAIN_MODEL §5.5 — superseded by PRD nesting until rewritten.

All models are `frozen=True, extra="forbid"` so unknown sibling keys fail at
ingest or round-trip merges — this is the explicit CS-135 AC.
"""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from classification.domain.contract_type import ContractType
from economics.domain.benchmark_comparison import BenchmarkComparison, Overcost


class DerivationStatus(StrEnum):
    """Persisted `derivation_status` values per `ECONOMIC_SUMMARY_CONTRACT.md`."""

    FULL = "full"
    INSUFFICIENT_DATA = "insufficient_data"


class EconomicWarning(BaseModel):
    """One row of `economic_summary.warnings`.

    `severity_suggested` is the literal `yellow | red` set from
    ECONOMIC_SUMMARY_CONTRACT.md (not the wider `info|low|medium|high` ladder
    initially considered in the planning phase — that lives in EPIC-06).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    severity_suggested: Literal["yellow", "red"]
    description: str = Field(min_length=1, max_length=2000)
    related_field: str | None = Field(default=None, max_length=64)


class FieldsExtracted(BaseModel):
    """Canonical `fields_extracted` block per PRD_F5 §5 / DOMAIN §5.5.

    Empty (all-None) instance maps to `{}` in JSON via the assembler's
    `model_dump(exclude_none=True)` call so the contract's "empty mapping"
    convention is honored.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    price_cash: Decimal | None = None
    down_payment: Decimal | None = None
    down_payment_pct: Decimal | None = None
    financed_amount: Decimal | None = None
    term_months: int | None = None
    annual_rate_pct: Decimal | None = None
    monthly_rate_pct: Decimal | None = None
    monthly_payment: Decimal | None = None
    payment_periodicity: str | None = None
    interest_calculation_base: str | None = None


class FieldsDerived(BaseModel):
    """Canonical `fields_derived` block per PRD_F5 §5 / DOMAIN §5.5."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_cost_paid: Decimal | None = None
    total_cost_vs_cash_multiplier: Decimal | None = None
    monthly_payment_theoretical: Decimal | None = None
    monthly_payment_coherent: bool | None = None


class EconomicSummary(BaseModel):
    """Top-level `ContractAnalysis.economic_summary` JSON envelope."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_type: ContractType
    currency: str = Field(default="USD", min_length=1, max_length=8)
    currency_conversion_note: str | None = Field(default=None, max_length=500)
    derivation_status: DerivationStatus | None = Field(default=None)
    fields_extracted: FieldsExtracted = Field(default_factory=FieldsExtracted)
    fields_derived: FieldsDerived = Field(default_factory=FieldsDerived)
    benchmark_comparisons: tuple[BenchmarkComparison, ...] = Field(default=())
    overcost: Overcost | None = Field(default=None)
    warnings: tuple[EconomicWarning, ...] = Field(default=())
    benchmark_version: str = Field(min_length=1, max_length=32)


__all__ = [
    "DerivationStatus",
    "EconomicSummary",
    "EconomicWarning",
    "FieldsDerived",
    "FieldsExtracted",
]
