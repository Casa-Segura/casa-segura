"""Aggregate a CS-113 `ContractExtraction` into a per-slot status payload (CS-116).

Pure function: takes the extractor's output and produces an
:class:`AggregatedExtraction` where every economic slot carries an
explicit :class:`ExtractionStatus`. Downstream layers (CS-137 persistence,
EPIC-06 rubric scoring, EPIC-05 economic analysis) read the status rather
than guessing from `None` / `0` / missing keys — satisfying PRD F5 BR-09
("no silent zero substitution") at the type level.

PRD references:
    - PRD_F2_CLASIFICACION US-04: per-field `extraction_status` semantics.
    - PRD_F5_ANALISIS_ECONOMICO US-01: `value is None or confidence < 0.5`
      ⇒ `not_present`.
    - PRD_F5_ANALISIS_ECONOMICO §6 / US-06 — warning code list (e.g.
      `interest_calculation_base_unfavorable`).
    - CS-114: `ECONOMICS_NOT_PRESENT_CUTOFF = 0.5` (single source of truth).

DDD note:
    Application layer. Imports domain DTOs + CS-114 policy. No Django,
    no httpx, no I/O. Designed to be unit-tested deterministically once
    CS-117 lands the test suite.
"""

from __future__ import annotations

from typing import Final

from classification.application.extraction_policy import REQUIRED_FIELDS_BY_TYPE
from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.confidence import (
    ECONOMICS_NOT_PRESENT_CUTOFF,
    ConfidenceBand,
)
from classification.domain.contract_extraction import ContractExtraction
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extracted_fields import ExtractedFields
from classification.domain.extraction_status import ExtractionStatus

# Field names that, when missing, trigger the
# `interest_calculation_base_unfavorable` precursor (CS-116 AC3). If any
# of these slots is non-PRESENT *and* the interest calculation base is
# `total_balance`, EPIC-05 should be warned that the contract may carry
# the Art. 12 LPC override risk.
_RATE_SLOTS_FOR_INTEREST_BASE: Final[tuple[str, ...]] = (
    "monthly_rate_pct",
    "interest_rate_pct",
)

# Closed list of warning precursor codes this aggregator can emit. Kept
# at module scope so callers / tests can introspect the surface without
# parsing PRD prose. Aligned with PRD_F5 §6 / US-06.
WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE: Final[str] = (
    "interest_calculation_base_unfavorable"
)


def aggregate_extraction(extraction: ContractExtraction) -> AggregatedExtraction:
    """Project a `ContractExtraction` into an `AggregatedExtraction`.

    Behaviour (CS-116 AC1-AC3):
        * Each field relevant to ``extraction.contract_type`` becomes an
          ``EconomicSlot``. "Relevant" = the union of the
          ``REQUIRED_FIELDS_BY_TYPE`` set for the contract type plus any
          field the extractor actually populated (so surplus extractions
          remain visible for QA).
        * Status is derived as:
            - ``INVALID``   when the field name appears in
              ``extraction.unverifiable_fields`` AND the extractor
              produced no value (i.e. it was demoted by CS-113's
              validator path).
            - ``NOT_PRESENT`` when value is ``None`` or confidence is
              missing or ``confidence < 0.5`` (PRD F5 US-01).
            - ``PRESENT``   otherwise.
            - ``AMBIGUOUS`` is reserved for a future extractor that
              surfaces an explicit ambiguity flag; CS-113 does not emit
              one today (TODO below). The status is wired into the model
              so EPIC-05 can begin consuming it without a model change.
        * ``unverifiable_fields`` = sorted ``field_name`` of every
          non-``PRESENT`` slot.
        * ``ambiguous_count`` = count of ``AMBIGUOUS`` slots (AC2 metric).
        * ``warning_precursors`` = codes whose triggering conditions are
          already determinable from the extraction (AC3).

    The function is pure — same input always produces the same output.
    """
    extracted = extraction.extracted_fields
    contract_type = extraction.contract_type

    # Build the set of slots to materialise: required for the type plus fields
    # the extractor actually populated. Fields that the extractor demoted
    # to `unverifiable` are kept too so callers see the INVALID slot even
    # if it is not in the required set for this contract type.
    required = set(REQUIRED_FIELDS_BY_TYPE.get(contract_type, set()))
    extractor_populated = {
        name
        for name in ExtractedFields.model_fields
        if getattr(extracted, name) is not None
    }
    demoted_invalid = set(extraction.unverifiable_fields)
    relevant_fields = required | extractor_populated | demoted_invalid

    invalid_set = _invalid_field_names(extraction)

    slots: dict[str, EconomicSlot] = {}
    for field_name in relevant_fields:
        value = getattr(extracted, field_name, None)
        band: ConfidenceBand | None = extraction.field_confidences.get(field_name)
        confidence_score = band.score if band is not None else None
        rationale = band.rationale if band is not None else None

        status = _derive_status(
            field_name=field_name,
            value=value,
            confidence=confidence_score,
            invalid_set=invalid_set,
        )

        slots[field_name] = EconomicSlot(
            field_name=field_name,
            status=status,
            value=value,
            confidence=confidence_score,
            rationale=rationale,
        )

    unverifiable_fields = sorted(
        name for name, slot in slots.items() if slot.status is not ExtractionStatus.PRESENT
    )
    ambiguous_count = sum(
        1 for slot in slots.values() if slot.status is ExtractionStatus.AMBIGUOUS
    )
    warning_precursors = _compute_warning_precursors(slots)

    return AggregatedExtraction(
        contract_type=contract_type,
        slots=slots,
        unverifiable_fields=unverifiable_fields,
        ambiguous_count=ambiguous_count,
        warning_precursors=warning_precursors,
    )


def _derive_status(
    *,
    field_name: str,
    value: float | int | str | None,
    confidence: float | None,
    invalid_set: set[str],
) -> ExtractionStatus:
    """Compute the :class:`ExtractionStatus` for a single field.

    Precedence (CS-116 AC1):
        1. ``INVALID`` if CS-113 demoted the field due to validator
           failure (i.e. the field name is in ``unverifiable_fields`` AND
           no value survived on `extracted_fields`).
        2. ``NOT_PRESENT`` if the value is ``None`` (contract silent) OR
           confidence is missing OR ``confidence < 0.5`` (PRD F5 US-01).
        3. ``PRESENT`` otherwise.

    ``AMBIGUOUS`` is intentionally NOT produced here: CS-113 does not yet
    surface an ambiguity signal. TODO(CS-113-followup): extend the
    extractor to publish ambiguity, then map it here before the
    ``NOT_PRESENT`` branch so it overrides confidence-based demotion.
    """
    if value is None and field_name in invalid_set:
        return ExtractionStatus.INVALID
    if value is None:
        return ExtractionStatus.NOT_PRESENT
    if confidence is None:
        return ExtractionStatus.NOT_PRESENT
    # CS-116 BVA row (`confidence` 0.49 vs 0.50): the cutoff is
    # *inclusive* on PRESENT — `>=` not `>`. A score of 0.50 passes;
    # 0.49 is demoted to NOT_PRESENT. `ECONOMICS_NOT_PRESENT_CUTOFF` is
    # the single source of truth (CS-114) and equals 0.5 exactly.
    if confidence < ECONOMICS_NOT_PRESENT_CUTOFF:
        return ExtractionStatus.NOT_PRESENT
    return ExtractionStatus.PRESENT


def _invalid_field_names(extraction: ContractExtraction) -> set[str]:
    """Return field names CS-113 demoted due to validator failure.

    CS-113 merges two distinct populations into ``unverifiable_fields``:
        * Required-but-missing fields (per BR-07 via ``classify_unverifiable``).
        * Fields the LLM tried to populate but failed pydantic validation
          (e.g. negative price) — those are demoted with no value left on
          ``extracted_fields``.

    For CS-116 we treat a name as ``INVALID`` only when it is in
    ``unverifiable_fields`` AND has no value on ``extracted_fields``.
    Names that are merely missing fall through to ``NOT_PRESENT`` later.

    Note: by construction every entry in ``unverifiable_fields`` has a
    ``None`` value on ``extracted_fields`` (CS-113 never demotes a field
    while keeping its value). The conjunction is kept explicit for
    defensive clarity should that invariant ever change.
    """
    invalid: set[str] = set()
    for name in extraction.unverifiable_fields:
        if name not in ExtractedFields.model_fields:
            continue
        if getattr(extraction.extracted_fields, name) is None:
            invalid.add(name)
    return invalid


def _compute_warning_precursors(slots: dict[str, EconomicSlot]) -> list[str]:
    """Determine which F5 US-06 warning codes the extraction already implies.

    Currently implemented (CS-116 AC3):
        * ``interest_calculation_base_unfavorable`` — fires when
          ``interest_calculation_base`` is ``PRESENT`` with value
          ``"total_balance"`` AND any of the rate slots
          (``monthly_rate_pct`` / ``interest_rate_pct``) is non-PRESENT.
          The contract carries the Art. 12 LPC override risk and EPIC-05
          can't fully derive the rate; the warning lets EPIC-06 surface
          a finding even without a complete economic computation.

    Extend this function as additional US-06 warnings become deterministic
    from extraction alone. Keep additions strictly ordered by the codes
    that PRD F5 §6 enumerates.
    """
    precursors: list[str] = []

    base_slot = slots.get("interest_calculation_base")
    if (
        base_slot is not None
        and base_slot.status is ExtractionStatus.PRESENT
        and base_slot.value == "total_balance"
    ):
        rate_unverifiable = any(
            (
                (rate_slot := slots.get(rate_name)) is None
                or rate_slot.status is not ExtractionStatus.PRESENT
            )
            for rate_name in _RATE_SLOTS_FOR_INTEREST_BASE
        )
        if rate_unverifiable:
            precursors.append(WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE)

    return precursors


__all__ = [
    "WARNING_PRECURSOR_INTEREST_BASE_UNFAVORABLE",
    "aggregate_extraction",
]
