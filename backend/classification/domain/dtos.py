"""Domain DTOs for the classification pipeline (CS-110).

Only the *minimum* envelope that CS-110 needs to ship a working primary
classification call. The full ``ClassificationResult`` defined in
``docs/analysis/F2_clasificacion/IMPLEMENTATION_PLAN.md`` (with
``elements_detected``, ``economic_fields_raw``, ``reclassification_*``
etc.) will be assembled by sibling tickets (CS-111 leasing detection,
CS-113 economic extraction, CS-114 nested schemas) on top of this base
shape — see PRD F2 §5.1.

DDD note: pydantic is treated as a domain-layer-safe library (it has no
Django / HTTP coupling), matching the convention already used by
``ingestion/domain``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from classification.domain.contract_type import ContractType


class ClassificationResult(BaseModel):
    """Primary classification envelope returned by ``ContractClassifier``.

    Fields map onto a subset of PRD F2 §8.1's LLM response:

    * ``contract_type``   ← ``contract_type``  (must be a ``ContractType``)
    * ``confidence``      ← ``confidence``     (0.0-1.0, per PRD US-01 bands)
    * ``reasoning``       ← ``reasoning``      (optional free-form Spanish)

    Sibling tickets extend this DTO; do not add fields here without
    updating CS-110, CS-114, and the consumers in F4/F5.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    contract_type: ContractType = Field(
        description="One of the nine PRD F2 §8.1 outcomes.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Model self-reported confidence; gated downstream by PRD F2 US-01 bands.",
    )
    reasoning: str | None = Field(
        default=None,
        description="Short Spanish justification surfaced for QA/logging only.",
    )
