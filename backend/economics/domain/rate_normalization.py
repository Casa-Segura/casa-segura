"""RateNormalization DTO — CS-131.

The normalized effective annual rate plus provenance for downstream
`fields_derived.annual_rate_pct` consumption. Pure pydantic v2 model; no
Django / infra imports (domain layer).

The math itself lives in `economics.application.rate_normalizer`; this module
only describes the carrier shape.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from classification.domain.extraction_status import ExtractionStatus


class RateNormalization(BaseModel):
    """Outcome of mapping raw monthly + annual rate slots to a single annual rate.

    Fields:
        annual_rate_pct: the canonical effective annual rate as Decimal in
            `[0, 1]`. `None` when neither input survived validation.
        status: `PRESENT` if `annual_rate_pct` is usable; `INVALID` if a
            value was supplied but failed PRD_F5 US-01 range checks;
            `NOT_PRESENT` if no raw input was usable.
        derivation_note: short machine-readable trace for the assembler:
            * `extracted_annual` — annual slot used directly.
            * `converted_from_monthly_compound` — `(1+m)^12 - 1` per BR-05.
            * `invalid_*` — explanatory tag when status == INVALID.
            * `not_expressed` — neither annual nor monthly was usable.
        warning_precursors: F5 US-06 warning codes triggered by the
            normalization step (subset of the canonical taxonomy). Codes:
              - `annual_rate_inconsistent_with_monthly`: annual present and
                monthly conversion disagrees beyond the 5% tolerance.
              - `annual_rate_not_expressed`: neither input was usable.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    annual_rate_pct: Decimal | None = Field(default=None)
    status: ExtractionStatus
    derivation_note: str | None = Field(default=None, max_length=64)
    warning_precursors: tuple[str, ...] = Field(default=())


__all__ = ["RateNormalization"]
