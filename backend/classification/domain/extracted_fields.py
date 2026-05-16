"""Structured extraction schema for classifier outputs.

PRD references:
    - PRD_F2_CLASIFICACION §8.5: canonical list of economic fields the
      classifier may extract (price_cash, down_payment, term_months, ...).
    - PRD_F2_CLASIFICACION US-02: project name extraction.
    - PRD_F2_CLASIFICACION US-04 + BR-07: missing fields are surfaced as
      `unverifiable` (see `classification.application.extraction_policy`)
      rather than treated as errors.

Design notes:
    - Every field defaults to `None` because the union of extractable
      fields across the eight covered contract types is wider than any
      single type's required set. The `ExtractionPolicy` module
      (`classify_unverifiable`) is what flags missing-but-required
      fields per `ContractType`.
    - Field names mirror the JSON keys returned by the §8.5 prompt where
      a 1:1 mapping exists. Where the PRD uses raw money amounts without
      a currency suffix, the canonical USD assumption (PRD_F2 §8.5 rule:
      "USD by default in El Salvador") is reflected by the `_usd` suffix.
    - Party identifiers (`seller_name`, `buyer_name`, `property_address`)
      are *transient* — they are identified during processing per PRD_F2
      §2 ("identified during processing but only the project name is
      preserved") and MUST NOT be persisted by callers. They live here
      so the LLM step can shuttle them within a single request lifecycle.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExtractedFields(BaseModel):
    """Union of structured fields the classifier may extract from a contract.

    All fields default to `None`. Per PRD_F2 BR-07 and CS-114, missing
    fields are not errors — `extraction_policy.classify_unverifiable`
    converts the per-type required set minus present fields into the
    `unverifiable_fields` list carried by `ContractExtraction`.

    Currency convention: all monetary `_usd` fields are denominated in
    USD. If the source contract uses SVC/colones, the LLM step applies
    the historical fixed rate (¢8.75 = $1) before populating these
    fields (PRD_F2 §8.5).
    """

    model_config = ConfigDict(extra="forbid", frozen=False)

    # --- Economic — purchase / installment / leasing ---
    purchase_price_usd: float | None = Field(
        default=None,
        ge=0,
        description="Total declared purchase price in USD (PRD_F2 §8.5 `price_cash`).",
    )
    down_payment_usd: float | None = Field(
        default=None,
        ge=0,
        description="Down payment / advance amount in USD (PRD_F2 §8.5 `down_payment`).",
    )
    down_payment_pct: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Down payment as decimal fraction (0.10 = 10%); §8.5 `down_payment_pct`.",
    )
    financed_amount_usd: float | None = Field(
        default=None,
        ge=0,
        description="Financed amount in USD (price minus down payment); §8.5 `financed_amount`.",
    )
    monthly_payment_usd: float | None = Field(
        default=None,
        ge=0,
        description="Periodic monthly installment in USD (§8.5 `monthly_payment`).",
    )
    installment_count: int | None = Field(
        default=None,
        ge=0,
        description="Total number of installments declared, when expressed as a count.",
    )
    term_months: int | None = Field(
        default=None,
        ge=0,
        description="Term in months (§8.5 `term_months`).",
    )

    # --- Economic — rates ---
    interest_rate_pct: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Effective annual interest rate as decimal (0.09 = 9%); "
            "§8.5 `annual_rate_pct`. Derived from monthly per BR-08 when only "
            "monthly is declared."
        ),
    )
    monthly_rate_pct: float | None = Field(
        default=None,
        ge=0.0,
        description="Monthly rate as decimal when the contract only states monthly (§8.5).",
    )

    # --- Economic — leasing / rental ---
    monthly_rent_usd: float | None = Field(
        default=None,
        ge=0,
        description="Monthly rent / canon in USD for ARV/ARC/APV/LEA contracts.",
    )
    deposit_usd: float | None = Field(
        default=None,
        ge=0,
        description="Refundable deposit in USD typically required by rental contracts.",
    )
    purchase_option_price_usd: float | None = Field(
        default=None,
        ge=0,
        description=(
            "Predefined end-of-term purchase option price for LEA/APV "
            "(PRD_F2 US-03 Art. 2 LAF indicator 2)."
        ),
    )

    # --- Currency + cadence ---
    currency: str | None = Field(
        default=None,
        max_length=8,
        description="Reported currency code (USD/SVC). Defaults to USD per §8.5.",
    )
    payment_periodicity: str | None = Field(
        default=None,
        max_length=16,
        description="One of 'monthly' | 'biweekly' | 'weekly' | 'other' (§8.5).",
    )
    interest_calculation_base: str | None = Field(
        default=None,
        max_length=32,
        description=(
            "One of 'outstanding_principal' | 'total_balance' | 'unspecified' "
            "(§8.5). `total_balance` is the Art. 12 LPC override trigger."
        ),
    )

    # --- Structural identifiers (transient — see module docstring) ---
    project_name_raw: str | None = Field(
        default=None,
        max_length=255,
        description="Project name as it appears in the contract (PRD_F2 US-02 `canonical_name`).",
    )
    property_address: str | None = Field(
        default=None,
        max_length=500,
        description="Property address. Transient: NEVER persisted (BR-04).",
    )
    seller_name: str | None = Field(
        default=None,
        max_length=255,
        description="Seller / lessor name. Transient: NEVER persisted (BR-04).",
    )
    buyer_name: str | None = Field(
        default=None,
        max_length=255,
        description="Buyer / lessee name. Transient: NEVER persisted (BR-04).",
    )


__all__ = ["ExtractedFields"]
