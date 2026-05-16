"""Per-contract-type extraction requirements and `unverifiable` computation.

PRD references:
    - PRD_F2_CLASIFICACION US-04: economic extraction is only invoked for
      types where it is meaningful (CVP, APV, LEA, FSV, ARV). Other types
      have no required economic fields.
    - PRD_F2_CLASIFICACION BR-07: missing required fields are not errors;
      they are surfaced as `unverifiable` for the rubric and economic
      layers to render as "no se pudo verificar" rather than as failed
      extraction.

`REQUIRED_FIELDS_BY_TYPE` is the single source of truth for what counts
as "missing-but-required" per contract type. Callers (the F2 service)
invoke `classify_unverifiable` after the LLM extraction step and store
the resulting list on `ContractExtraction.unverifiable_fields`.

Field names MUST match attribute names on
`classification.domain.extracted_fields.ExtractedFields` — the
`_validate_field_names_known` module-import-time assertion enforces this
so a typo in a required-set declaration fails loudly at import rather
than silently flagging a real field as missing on every analysis.
"""

from __future__ import annotations

from classification.domain.contract_type import ContractType
from classification.domain.extracted_fields import ExtractedFields

# Mapping of contract type → required field attribute names on `ExtractedFields`.
#
# Notes per PRD_F2:
#   - CVC (cash purchase): price + structural identifiers; no financing fields.
#   - CVP (installment purchase): full economic schedule.
#   - APV (lease-with-promise-to-sell): rental cadence + total price + purchase option.
#   - LEA (financial leasing): rental cadence + purchase option price (Art. 2 LAF #2).
#   - FSV (FSV-financed): full schedule like CVP, project name is institutional.
#   - ARV / ARC (residential / commercial lease): rent + deposit + cadence.
#   - IVU (institutional adjudication): only structural identifier required.
#   - NOT_CLASSIFIABLE: nothing is required (the submission will not be analyzed).
REQUIRED_FIELDS_BY_TYPE: dict[ContractType, set[str]] = {
    ContractType.CVC: {
        "purchase_price_usd",
        "currency",
        "project_name_raw",
    },
    ContractType.CVP: {
        "purchase_price_usd",
        "down_payment_usd",
        "financed_amount_usd",
        "term_months",
        "monthly_payment_usd",
        "interest_rate_pct",
        "interest_calculation_base",
        "payment_periodicity",
        "currency",
        "project_name_raw",
    },
    ContractType.APV: {
        "purchase_price_usd",
        "monthly_rent_usd",
        "term_months",
        "purchase_option_price_usd",
        "payment_periodicity",
        "currency",
        "project_name_raw",
    },
    ContractType.LEA: {
        "monthly_rent_usd",
        "term_months",
        "purchase_option_price_usd",
        "interest_rate_pct",
        "payment_periodicity",
        "currency",
        "project_name_raw",
    },
    ContractType.FSV: {
        "purchase_price_usd",
        "down_payment_usd",
        "financed_amount_usd",
        "term_months",
        "monthly_payment_usd",
        "interest_rate_pct",
        "payment_periodicity",
        "currency",
        "project_name_raw",
    },
    ContractType.ARV: {
        "monthly_rent_usd",
        "deposit_usd",
        "term_months",
        "payment_periodicity",
        "currency",
        "project_name_raw",
    },
    ContractType.ARC: {
        "monthly_rent_usd",
        "deposit_usd",
        "term_months",
        "payment_periodicity",
        "currency",
        "project_name_raw",
    },
    ContractType.IVU: {
        "project_name_raw",
    },
    ContractType.NOT_CLASSIFIABLE: set(),
}


def _validate_field_names_known() -> None:
    """Assert that every required field name refers to a real `ExtractedFields` attr.

    Runs at import time. A typo in `REQUIRED_FIELDS_BY_TYPE` would otherwise
    leak through as a spurious `unverifiable` entry on every analysis.
    """
    known_attrs = set(ExtractedFields.model_fields.keys())
    for contract_type, required in REQUIRED_FIELDS_BY_TYPE.items():
        unknown = required - known_attrs
        if unknown:
            raise RuntimeError(
                f"REQUIRED_FIELDS_BY_TYPE[{contract_type.name}] references "
                f"unknown ExtractedFields attributes: {sorted(unknown)}"
            )


_validate_field_names_known()


def classify_unverifiable(
    extracted: ExtractedFields,
    contract_type: ContractType,
) -> list[str]:
    """Return required-but-missing field names for the given contract type.

    Per BR-07, "missing" means `None` (the LLM did not surface the field).
    Sentinels like empty strings or zero are NOT treated as missing —
    they represent real extracted values that downstream validation
    (F5) is responsible for sanity-checking.

    The returned list is sorted for stable persistence (so two identical
    extractions produce byte-identical `unverifiable_fields` arrays for
    diffing / cache keys).

    Examples (no PII):
        >>> from classification.domain.contract_type import ContractType
        >>> from classification.domain.extracted_fields import ExtractedFields
        >>> classify_unverifiable(ExtractedFields(), ContractType.CVC)
        ['currency', 'project_name_raw', 'purchase_price_usd']
        >>> classify_unverifiable(
        ...     ExtractedFields(purchase_price_usd=80000.0, currency="USD", project_name_raw="ejemplo"),
        ...     ContractType.CVC,
        ... )
        []
    """
    required = REQUIRED_FIELDS_BY_TYPE.get(contract_type, set())
    missing = [name for name in required if getattr(extracted, name) is None]
    return sorted(missing)


__all__ = [
    "REQUIRED_FIELDS_BY_TYPE",
    "classify_unverifiable",
]
