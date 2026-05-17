"""Structural boolean flags surfaced by the §8.1 classifier (PRD_F2 §US-05).

PRD references:
    - PRD_F2_CLASIFICACION §5.1: `elements_detected` JSONB column shape.
    - PRD_F2_CLASIFICACION §US-05: enumerated list of clause-level flags
      the classifier must surface so EPIC-06 evaluators can dispatch on
      them without re-reading the contract.

Design notes:
    - Closed set: 11 booleans. Adding one requires a coordinated update
      with EPIC-06 (rubric evaluators key off these flags) — `extra="forbid"`
      makes the schema drift impossible to introduce silently.
    - All flags default to `False`. The classifier prompt explicitly asks
      the LLM to flip a flag only when the corresponding clause is present;
      absence is the safe default.
    - This DTO is the persistence-oriented projection of the §US-05 keys
      that lands on `ContractAnalysis.elements_detected` (added by migration
      `platform_core/0005_classification_f2_fields.py`). No PII surface
      (BR-04 / BR-07) — flags are categorical, not textual.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ElementsDetected(BaseModel):
    """Closed catalogue of structural clauses surfaced by §8.1 classification.

    Each field is `True` only when the §8.1 prompt's response affirms the
    presence of the corresponding clause. Downstream rubric evaluators
    (EPIC-06) treat the absence of a flag as "not detected" — never as
    "unknown" — so the classifier must answer all 11 keys per submission.

    Cross-references (PRD_F2 §US-05 / RUBRICA §16):
        public_deed                       → applicability + B6 weight
        arbitration_clause                → E4 evaluator dispatch
        warranty_exemption_clause         → E1 / E7 override candidate
        blank_signature_clause            → critical override (RUBRICA §2.2)
        unilateral_modification_clause    → C5 evaluator + override Art. 12 LPC
        automatic_acceleration_clause     → B3 evaluator + override candidate
        disproportionate_late_fee         → B5 evaluator
        prepayment_penalty_clause         → B7 evaluator
        notary_designation_clause         → D3 evaluator
        mandatory_arbitration             → E4 / override Art. 18 LPC
        forced_jurisdiction_clause        → E5 evaluator
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    public_deed: bool = False
    arbitration_clause: bool = False
    warranty_exemption_clause: bool = False
    blank_signature_clause: bool = False
    unilateral_modification_clause: bool = False
    automatic_acceleration_clause: bool = False
    disproportionate_late_fee: bool = False
    prepayment_penalty_clause: bool = False
    notary_designation_clause: bool = False
    mandatory_arbitration: bool = False
    forced_jurisdiction_clause: bool = False


__all__ = ["ElementsDetected"]
