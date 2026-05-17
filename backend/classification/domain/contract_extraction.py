"""Top-level wrapper that bundles classifier output for downstream persistence.

PRD references:
    - PRD_F2_CLASIFICACION §6.2: envelope shape published to F4/F5 after
      classification (`classification`, `economic_fields_raw`,
      `elements_detected`).
    - PRD_F2_CLASIFICACION US-04 + BR-07: missing required fields surface
      as `unverifiable_fields` rather than hard errors.
    - CS-114: this is the model downstream services persist; aligns with
      `ContractAnalysis` columns `contract_type`, `classification_confidence`,
      `reclassification_indicators`, plus the in-memory extraction payload
      that F5 consumes (NOT persisted directly per US-04).

This wrapper sits *one level above* the §8.5-shaped `EconomicFieldsRaw`
DTO outlined in `docs/analysis/F2_clasificacion/IMPLEMENTATION_PLAN.md`:
it captures the *normalized* extraction surface (the union of fields the
classifier can produce) plus per-field confidence bands and the
unverifiable list — i.e. the persistence-oriented projection consumed
by F4 (rubric) and F5 (economic analysis).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from classification.domain.confidence import ConfidenceBand
from classification.domain.contract_type import ContractType
from classification.domain.extracted_fields import ExtractedFields


class ContractExtraction(BaseModel):
    """Persistence-oriented projection of a single classification result.

    Fields:
        contract_type: final classified type (post-reclassification if §8.4
            triggered). One of the `ContractType` literals; values outside
            the closed set are rejected at parse time per CS-114 AC.
        extracted_fields: union of structured fields; missing entries are
            `None` and are flagged via `unverifiable_fields`.
        field_confidences: per-field `ConfidenceBand` keyed by the same
            attribute name used on `ExtractedFields`. Bands are optional —
            a field absent from this map means the classifier did not
            attempt extraction (treat as `unverifiable`).
        unverifiable_fields: required-but-missing field names for this
            `contract_type`, computed by
            `classification.application.extraction_policy.classify_unverifiable`.
    """

    model_config = ConfigDict(extra="forbid")

    contract_type: ContractType
    extracted_fields: ExtractedFields = Field(default_factory=ExtractedFields)
    field_confidences: dict[str, ConfidenceBand] = Field(default_factory=dict)
    unverifiable_fields: list[str] = Field(default_factory=list)
    ambiguous_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Field names the LLM flagged as ambiguous (conflicting figures in "
            "the contract, or `extraction_status=ambiguous` in the per-field "
            "envelope). Value is suppressed for these fields; downstream "
            "`aggregate_extraction` (CS-116) maps the entry to "
            "`ExtractionStatus.AMBIGUOUS` rather than substituting a numeric "
            "zero (PRD_F5 BR-09 honesty)."
        ),
    )

    @model_validator(mode="after")
    def _confidence_keys_are_known_fields(self) -> ContractExtraction:
        """Reject confidence keys that don't match `ExtractedFields` attributes.

        Prevents silent typos that would otherwise leave persisted confidence
        bands unjoinable with the extracted values they describe.
        """
        known = set(ExtractedFields.model_fields.keys())
        unknown = set(self.field_confidences.keys()) - known
        if unknown:
            raise ValueError(f"field_confidences references unknown ExtractedFields keys: {sorted(unknown)}")

        unknown_ambiguous = set(self.ambiguous_fields) - known
        if unknown_ambiguous:
            raise ValueError(
                f"ambiguous_fields references unknown ExtractedFields keys: {sorted(unknown_ambiguous)}",
            )
        return self


__all__ = ["ContractExtraction"]
