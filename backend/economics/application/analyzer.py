"""CS-135: EconomicSummary assembler.

Orchestrates the deterministic F5 pipeline:

    AggregatedExtraction
      ├─ rate_normalizer.normalize_annual_rate    (CS-131)
      ├─ total_cost.compute_total_cost            (CS-133)
      ├─ payment_ratio.compute_monthly_ratio      (CS-132)
      └─ benchmark_comparator                     (CS-134)

and emits one `EconomicSummary` matching the cross-team
`docs/analysis/F5_analisis_economico/ECONOMIC_SUMMARY_CONTRACT.md`.

`derivation_status` is set per ECONOMIC_SUMMARY_CONTRACT.md:
    * `full` when at least one derived field is populated.
    * `insufficient_data` when nothing usable came through (CS-137 handles
      the renormalization details; this module just gates the status).

The assembler is **deterministic and LLM-free** (PRD_F5 BR-13).
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

from classification.domain.aggregated_extraction import AggregatedExtraction
from classification.domain.economic_slot import EconomicSlot
from classification.domain.extraction_status import ExtractionStatus
from economics.application.benchmark_comparator import (
    RateBand,
    compare_rate,
    compute_overcost,
    select_segment,
)
from economics.application.catalog import BenchmarkCatalog
from economics.application.payment_ratio import compute_monthly_ratio
from economics.application.rate_normalizer import normalize_annual_rate
from economics.application.renormalizer import detect_precursors
from economics.application.total_cost import compute_total_cost
from economics.application.warning_catalog import to_warning_or_none
from economics.domain.benchmark_comparison import BenchmarkComparison, BenchmarkSegment
from economics.domain.economic_summary import (
    DerivationStatus,
    EconomicSummary,
    EconomicWarning,
    FieldsDerived,
    FieldsExtracted,
)

_QUANTIZE_DEC = Decimal("0.0001")


def analyze(
    extraction: AggregatedExtraction,
    *,
    catalog: BenchmarkCatalog,
    has_developer_direct_hint: bool = False,
) -> EconomicSummary:
    """Build the full `EconomicSummary` for one classification result.

    Args:
        extraction: F2 aggregated payload (slots + warning precursors).
        catalog: hydrated `BenchmarkCatalog` for the active version.
        has_developer_direct_hint: lets CS-112 (eventual orchestrator)
            override segment selection when classification flags a
            developer-direct financing arrangement.
    """

    # 1. Normalize the annual rate (CS-131).
    rate = normalize_annual_rate(extraction)

    # 2. Compute total-cost bundle (CS-133), using the IVU benchmark for
    #    term_excessive detection when available.
    ivu_max = _benchmark_value(catalog, "credit_term_ivu_max_months")
    bundle = compute_total_cost(
        extraction,
        annual_rate_pct=rate.annual_rate_pct,
        ivu_max_term_months=int(ivu_max) if ivu_max is not None else None,
    )

    # 3. Monthly-payment ratio band (CS-132).
    ratio = compute_monthly_ratio(
        extraction,
        healthy_max=_benchmark_value(catalog, "monthly_payment_ratio_healthy_max") or Decimal("1.2"),
        high_max=_benchmark_value(catalog, "monthly_payment_ratio_high_max") or Decimal("1.4"),
        excessive_min=_benchmark_value(catalog, "monthly_payment_ratio_excessive_min") or Decimal("1.7"),
    )

    # 4. Build benchmark comparisons + overcost (CS-134).
    comparisons, overcost = _build_comparisons_and_overcost(
        extraction=extraction,
        rate_annual_pct=rate.annual_rate_pct,
        bundle=bundle,
        catalog=catalog,
        ratio_value=ratio.ratio,
        has_developer_direct_hint=has_developer_direct_hint,
    )

    # 5. Aggregate warning precursors (including CS-137 renormalizer
    #    cross-slot checks) and translate to structured warnings.
    precursor_codes: list[str] = []
    precursor_codes.extend(extraction.warning_precursors)
    precursor_codes.extend(rate.warning_precursors)
    precursor_codes.extend(bundle.warning_precursors)
    precursor_codes.extend(detect_precursors(extraction, bundle))
    warnings = _build_warnings(precursor_codes)

    # 6. Build top-level summary.
    fields_extracted = _build_fields_extracted(extraction)
    fields_derived = _build_fields_derived(rate, bundle)

    return EconomicSummary(
        contract_type=extraction.contract_type,
        currency=_resolve_currency(extraction),
        currency_conversion_note=None,
        derivation_status=_derive_status(fields_derived),
        fields_extracted=fields_extracted,
        fields_derived=fields_derived,
        benchmark_comparisons=tuple(comparisons),
        overcost=overcost,
        warnings=tuple(warnings),
        benchmark_version=catalog.version,
    )


# ─── Internals ───────────────────────────────────────────────────────────────


def _benchmark_value(catalog: BenchmarkCatalog, key: str) -> Decimal | None:
    entry = catalog.get(key)
    if entry is None:
        return None
    return entry.value


def _benchmark_source(catalog: BenchmarkCatalog, key: str) -> str:
    entry = catalog.get(key)
    return entry.source if entry is not None else ""


def _build_comparisons_and_overcost(
    *,
    extraction: AggregatedExtraction,
    rate_annual_pct: Decimal | None,
    bundle,  # TotalCostBundle
    catalog: BenchmarkCatalog,
    ratio_value: Decimal | None,
    has_developer_direct_hint: bool,
):
    comparisons: list[BenchmarkComparison] = []
    overcost = None

    if rate_annual_pct is not None:
        segment = select_segment(extraction.contract_type, has_developer_direct_hint)
        rate_band = _build_rate_band(catalog, segment)
        if rate_band is not None:
            comparisons.append(
                compare_rate(
                    contract_annual_pct=rate_annual_pct,
                    segment_band=rate_band,
                    segment=segment,
                )
            )
            term_slot = _slot_value(extraction.slots.get("term_months"))
            down_slot = _slot_value(extraction.slots.get("down_payment_usd"))
            if (
                bundle.financed_amount_resolved is not None
                and term_slot is not None
                and bundle.total_cost_paid is not None
            ):
                overcost = compute_overcost(
                    contract_annual_pct=rate_annual_pct,
                    contract_term_months=int(term_slot),
                    contract_financed_amount=bundle.financed_amount_resolved,
                    contract_total_cost_paid=bundle.total_cost_paid,
                    segment_band=rate_band,
                    segment=segment,
                    contract_down_payment=Decimal(str(down_slot)) if down_slot is not None else None,
                )

    # Monthly-payment-ratio comparison row when the ratio is computable.
    if ratio_value is not None:
        healthy_max = _benchmark_value(catalog, "monthly_payment_ratio_healthy_max")
        if healthy_max is not None:
            delta_pp = None  # ratio comparisons surface the raw ratio, not a pp delta.
            assessment = _ratio_assessment(ratio_value, healthy_max)
            comparisons.append(
                BenchmarkComparison(
                    metric="monthly_payment_ratio",
                    metric_label="Cuota mensual vs. línea base lineal",
                    contract_value=ratio_value,
                    benchmark_value=healthy_max,
                    benchmark_key="monthly_payment_ratio_healthy_max",
                    benchmark_source=_benchmark_source(catalog, "monthly_payment_ratio_healthy_max"),
                    delta_pct_points=delta_pp,
                    assessment=assessment,
                )
            )

    return comparisons, overcost


def _ratio_assessment(ratio: Decimal, healthy_max: Decimal) -> str:
    # The ratio's `_classify` already mapped a band; here we surface a
    # 4-value `assessment` aligned with DOMAIN §5.6: ratios at or below
    # the healthy_max are `within_market`; any ratio above is at least
    # `above_market`. EPIC-06's B5 evaluator owns the finer interpretation.
    if ratio <= healthy_max:
        return "within_market"
    return "above_market"


def _build_rate_band(catalog: BenchmarkCatalog, segment: BenchmarkSegment) -> RateBand | None:
    """Assemble the `RateBand` for the chosen segment from catalog entries."""

    if segment == BenchmarkSegment.FSV:
        min_v = _benchmark_value(catalog, "fsv_rate_min")
        max_v = _benchmark_value(catalog, "fsv_rate_max")
        mid_v = _benchmark_value(catalog, "fsv_rate_mid")
        key = "fsv_rate_mid"
        source = _benchmark_source(catalog, key)
    elif segment == BenchmarkSegment.DEVELOPER_DIRECT:
        min_v = _benchmark_value(catalog, "developer_direct_rate_min")
        max_v = _benchmark_value(catalog, "developer_direct_rate_max")
        # Catalog may not ship an explicit mid for developer-direct; derive it
        # locally as the midpoint of min/max when both are present.
        mid_v = (
            ((min_v + max_v) / Decimal("2")).quantize(_QUANTIZE_DEC, rounding=ROUND_HALF_EVEN)
            if (min_v is not None and max_v is not None)
            else None
        )
        # No persisted mid_benchmark_key for developer_direct; cite the upper
        # bound as the comparison anchor.
        key = "developer_direct_rate_max"
        source = _benchmark_source(catalog, key)
    else:
        min_v = _benchmark_value(catalog, "bank_mortgage_rate_min")
        max_v = _benchmark_value(catalog, "bank_mortgage_rate_max")
        mid_v = _benchmark_value(catalog, "bank_mortgage_rate_mid")
        key = "bank_mortgage_rate_mid"
        source = _benchmark_source(catalog, key)

    if min_v is None or max_v is None or mid_v is None:
        return None
    return RateBand(
        min_value=min_v,
        max_value=max_v,
        mid_value=mid_v,
        mid_benchmark_key=key,
        mid_benchmark_source=source,
    )


def _build_warnings(codes: list[str]) -> list[EconomicWarning]:
    """Translate precursor codes to structured warnings, deduping by `(code, related_field)`."""

    seen: set[tuple[str, str | None]] = set()
    warnings: list[EconomicWarning] = []
    for code in codes:
        spec = to_warning_or_none(code)
        if spec is None:
            continue
        key = (code, spec.related_field)
        if key in seen:
            continue
        seen.add(key)
        warnings.append(
            EconomicWarning(
                code=code,
                severity_suggested=spec.severity_suggested,
                description=spec.description,
                related_field=spec.related_field,
            )
        )
    return warnings


def _build_fields_extracted(extraction: AggregatedExtraction) -> FieldsExtracted:
    return FieldsExtracted(
        price_cash=_decimal(_slot_value(extraction.slots.get("purchase_price_usd"))),
        down_payment=_decimal(_slot_value(extraction.slots.get("down_payment_usd"))),
        down_payment_pct=_decimal(_slot_value(extraction.slots.get("down_payment_pct"))),
        financed_amount=_decimal(_slot_value(extraction.slots.get("financed_amount_usd"))),
        term_months=(
            int(_slot_value(extraction.slots.get("term_months")))
            if _slot_value(extraction.slots.get("term_months")) is not None
            else None
        ),
        annual_rate_pct=_decimal(_slot_value(extraction.slots.get("interest_rate_pct"))),
        monthly_rate_pct=_decimal(_slot_value(extraction.slots.get("monthly_rate_pct"))),
        monthly_payment=_decimal(_slot_value(extraction.slots.get("monthly_payment_usd"))),
        payment_periodicity=_string_slot(extraction.slots.get("payment_periodicity")),
        interest_calculation_base=_string_slot(extraction.slots.get("interest_calculation_base")),
    )


def _build_fields_derived(rate, bundle) -> FieldsDerived:
    return FieldsDerived(
        total_cost_paid=bundle.total_cost_paid,
        total_cost_vs_cash_multiplier=bundle.total_cost_vs_cash_multiplier,
        monthly_payment_theoretical=bundle.monthly_payment_theoretical,
        monthly_payment_coherent=bundle.monthly_payment_coherent,
    )


def _derive_status(derived: FieldsDerived) -> DerivationStatus | None:
    """Return `full` when any derived field is populated; else `insufficient_data`."""

    populated = any(
        value is not None
        for value in (
            derived.total_cost_paid,
            derived.total_cost_vs_cash_multiplier,
            derived.monthly_payment_theoretical,
        )
    )
    return DerivationStatus.FULL if populated else DerivationStatus.INSUFFICIENT_DATA


def _resolve_currency(extraction: AggregatedExtraction) -> str:
    slot = extraction.slots.get("currency")
    if slot is None or slot.status != ExtractionStatus.PRESENT:
        return "USD"
    if isinstance(slot.value, str) and slot.value:
        return slot.value
    return "USD"


def _slot_value(slot: EconomicSlot | None):
    if slot is None or slot.status != ExtractionStatus.PRESENT:
        return None
    return slot.value if slot.value is not None else None


def _string_slot(slot: EconomicSlot | None) -> str | None:
    value = _slot_value(slot)
    return value if isinstance(value, str) else None


def _decimal(value) -> Decimal | None:
    if value is None or not isinstance(value, (int, float)):
        return None
    return Decimal(str(value)).quantize(_QUANTIZE_DEC, rounding=ROUND_HALF_EVEN)


__all__ = ["analyze"]
