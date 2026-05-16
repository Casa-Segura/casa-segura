"""Aggregated extraction payload bundling per-slot status (CS-116).

PRD references:
    - PRD_F2_CLASIFICACION §6.2: F2 publishes `economic_fields_raw` to F4
      and F5. CS-116 enriches that envelope with explicit per-slot status
      markers so downstream layers never confuse "missing" with "zero".
    - PRD_F5_ANALISIS_ECONOMICO US-01 + BR-09: F5 must not invent figures
      for absent / low-confidence fields.
    - PRD_F5_ANALISIS_ECONOMICO §6 / US-06: F5 emits a closed-set of
      `warnings[]`. This wrapper exposes `warning_precursors` — codes
      whose triggering conditions are already detectable from the
      extraction alone (e.g. `interest_calculation_base_unfavorable`
      when base is `total_balance` but the rate is unverifiable).
    - DOMAIN_MODEL §5.5: `EconomicSummary.fields_extracted`. CS-137 owns
      the live persistence wiring; this DTO is the in-memory contract.

DDD note:
    Domain layer — pydantic v2 only, no Django / infra imports.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from classification.domain.contract_type import ContractType
from classification.domain.economic_slot import EconomicSlot


class AggregatedExtraction(BaseModel):
    """Per-contract aggregated economic extraction with explicit status flags.

    Fields:
        contract_type: classified type the aggregation was scoped to.
            Determines which fields are considered "relevant" (via
            `REQUIRED_FIELDS_BY_TYPE`) and therefore which slots appear
            even when the LLM did not surface them.
        slots: map of `field_name` → `EconomicSlot`. Contains one entry
            per relevant field for `contract_type` plus any field the
            extractor populated even if not formally required (so QA can
            see surplus extractions).
        unverifiable_fields: lexicographically-sorted list of `field_name`s
            whose `status != PRESENT`. This is the "no figure available"
            list the rubric engine reads (EPIC-06) and CS-137 persists.
        ambiguous_count: number of slots with `status == AMBIGUOUS`.
            Surfaced for metrics observability (CS-116 AC2 — count of
            ambiguous fields).
        warning_precursors: F5 US-06 warning codes whose triggering
            conditions are already determinable from extraction alone.
            Currently emitted codes:
              - `interest_calculation_base_unfavorable` (CS-116 AC3): the
                `interest_calculation_base` slot is `PRESENT` with value
                `total_balance` and at least one rate slot
                (`monthly_rate_pct` or `interest_rate_pct`) is missing /
                ambiguous / invalid. EPIC-05 may translate this into the
                full Art. 12 LPC warning.
            The list is extensible — add new precursor codes here as F5
            US-06 cases become deterministically detectable from
            extraction without running the F5 deterministic pipeline.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    contract_type: ContractType
    slots: dict[str, EconomicSlot] = Field(default_factory=dict)
    unverifiable_fields: list[str] = Field(default_factory=list)
    ambiguous_count: int = Field(default=0, ge=0)
    warning_precursors: list[str] = Field(default_factory=list)


__all__ = ["AggregatedExtraction"]
