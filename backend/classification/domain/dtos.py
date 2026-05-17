"""Domain DTOs for the classification pipeline (CS-110 + CS-114).

CS-110 shipped the primary-call envelope (`contract_type`, `confidence`,
`reasoning`). CS-114 extends it with:

    - `classification_attempts`  -> PRD_F2 §5.1 / §US-01 (1 single call,
      2 if the §8.3 validator fired).
    - `indicators_found`         -> PRD_F2 §8.1 free-text justifications,
      validated through `IndicatorsFound`.
    - `elements_detected`        -> PRD_F2 §US-05 closed boolean catalogue
      via `ElementsDetected`.

The orchestrator (PR-6) is responsible for populating `attempts` and the
two nested DTOs after running classification + leasing detection. This
file does NOT take a dependency on Django, HTTP, or any infra — pydantic
v2 is treated as domain-layer safe (same convention as `ingestion/domain`).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from classification.domain.contract_type import ContractType
from classification.domain.elements_detected import ElementsDetected
from classification.domain.indicators import IndicatorsFound


class ClassificationResult(BaseModel):
    """Classifier envelope produced by ``ContractClassifier``.

    Persisted projection lands on `ContractAnalysis` (see migration
    `platform_core/0005_classification_f2_fields.py`):

    * ``contract_type``            → `contract_type`
    * ``confidence``               → `classification_confidence`
    * ``classification_attempts``  → `classification_attempts`
    * ``elements_detected``        → `elements_detected` (JSONB)
    * ``indicators_found``         → audit-only (not persisted columnwise;
       carried in observability logs and the §6.2 envelope for F4/F5).

    Sibling tickets MUST NOT add fields without updating CS-110, CS-114,
    the migration set, and the consumers in F4/F5.
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
    classification_attempts: int = Field(
        default=1,
        ge=1,
        le=3,
        description=(
            "1 when the primary §8.1 call is accepted as-is, 2 when the §8.3 "
            "validator fired. CHECK constraint on the persisted column caps at 3."
        ),
    )
    indicators_found: IndicatorsFound = Field(
        default_factory=IndicatorsFound,
        description="§8.1 free-text justifications (closed list, length-capped).",
    )
    elements_detected: ElementsDetected = Field(
        default_factory=ElementsDetected,
        description="§US-05 closed boolean catalogue; defaults to all-False.",
    )
