"""Pure score-aggregation core (CS-152, CS-155, CS-156, CS-157).

Implements the algorithm transcribed verbatim from RUBRICA_CONTRATO §10:

1. Override gate — any evaluation carrying ``override_triggered`` collapses
   the result to ``score_total=0.0`` / ``band=red`` (CS-157).
2. Applicability filter — evaluations are already gated by the caller, but
   ``compute_category_scores`` defensively checks the ``applicable`` flag
   and dedupes by ``criterion_id`` (CS-155 AC: no silent double count).
3. Per-category renormalization — score_cat = Σ wᵢ·sᵢ / Σ wᵢ with the
   ``w_i`` taken from the ``Criterion.weight_in_category`` rows the seed
   migration loaded (CS-152).
4. Global renormalization — global weights A=0.20, B=0.30, C=0.20,
   D=0.15, E=0.10, F=0.05 are scaled over the categories that have at
   least one applicable criterion (CS-152, CS-155).
5. Banker's-rounded ``score_total`` (decimal HALF_EVEN at 1 decimal place)
   then mapped to a band per §2.1 (CS-156).

The module is **deterministic and LLM-free**. The caller is responsible
for resolving unverifiable / failed evaluations into worst-case scores
*before* invoking this calculator (see ``unverifiable.resolve``).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from rubric.domain.band import Band, OverrideCode
from rubric.domain.entities import CategoryLiteral, CategoryScore, CriterionEvaluation

# Global category weights per RUBRICA_CONTRATO §2 / §10.
GLOBAL_CATEGORY_WEIGHTS: dict[CategoryLiteral, Decimal] = {
    "A": Decimal("0.20"),
    "B": Decimal("0.30"),
    "C": Decimal("0.20"),
    "D": Decimal("0.15"),
    "E": Decimal("0.10"),
    "F": Decimal("0.05"),
}

CATEGORY_NAMES_ES: dict[CategoryLiteral, str] = {
    "A": "Validez legal y formal",
    "B": "Salud económica",
    "C": "Garantías para el comprador o arrendatario",
    "D": "Riesgos del inmueble",
    "E": "Cláusulas y prácticas abusivas",
    "F": "Transparencia y claridad",
}

_FLOAT_TOLERANCE = Decimal("1e-9")
_ONE_DECIMAL = Decimal("0.1")


class NoApplicableCriteriaError(ValueError):
    """Raised when no applicable evaluations are provided to aggregation.

    The pipeline must short-circuit upstream with ``Band.NOT_ANALYZABLE``
    before invoking the calculator — this guard turns the silent-zero
    failure mode into an explicit error (CS-152 BVA: empty applicable set).
    """


@dataclass(frozen=True)
class AggregationResult:
    """Outcome of ``aggregate_total`` — see CS-152 / CS-157 contracts."""

    score_total: float
    band: Band
    override_active: bool
    override_triggered: tuple[OverrideCode, ...]
    category_scores: tuple[CategoryScore, ...]


# ── CS-152: single place for 1-decimal banker's rounding (BVA tests import) ─


def banker_round_score_total(value: float | Decimal) -> Decimal:
    """Round a raw aggregate to 1 decimal with ``ROUND_HALF_EVEN`` (CS-152)."""

    v = Decimal(str(value)) if not isinstance(value, Decimal) else value
    return v.quantize(_ONE_DECIMAL, rounding=ROUND_HALF_EVEN)


# ── CS-156: band assignment ─────────────────────────────────────────────


def assign_band(score_total: float | Decimal) -> Band:
    """Map a *rounded* total score to a band per RUBRICA_CONTRATO §2.1.

    Inclusive lower bounds: 8.0 → GREEN, 5.0 → YELLOW, 0.0 → RED.
    The caller is responsible for rounding to 1 decimal first — boundary
    fixtures share the same rounding module so 7.95 → 8.0 → green and
    7.949 → 7.9 → yellow per CS-156 BVA.
    """

    score = Decimal(str(score_total)) if not isinstance(score_total, Decimal) else score_total
    if score >= Decimal("8.0"):
        return Band.GREEN
    if score >= Decimal("5.0"):
        return Band.YELLOW
    return Band.RED


# ── CS-155: applicability filtering + per-category renormalization ──────


def compute_category_scores(
    evaluations: list[CriterionEvaluation],
    *,
    contract_type: str | None = None,
) -> list[CategoryScore]:
    """Compute one ``CategoryScore`` per category that has applicable rows.

    ``evaluations`` are expected to carry the resolved score (unverifiable
    rows have already been substituted with their catalog worst-case via
    ``unverifiable.resolve``).

    ``contract_type`` is informational — applicability is taken from each
    evaluation's ``applicable`` flag, which the caller must set by
    intersecting ``Criterion.applicable_types`` with the analysis's type
    (CS-155 AC: criteria that do not apply are absent, not zeroed).
    """

    if not evaluations:
        return []

    _reject_duplicates(evaluations)

    by_category: dict[CategoryLiteral, list[CriterionEvaluation]] = {}
    totals_by_category: dict[CategoryLiteral, int] = {}
    for ev in evaluations:
        totals_by_category[ev.category] = totals_by_category.get(ev.category, 0) + 1
        if ev.applicable:
            by_category.setdefault(ev.category, []).append(ev)

    out: list[CategoryScore] = []
    for category in ("A", "B", "C", "D", "E", "F"):
        applicable_rows = by_category.get(category, [])
        if not applicable_rows:
            continue
        score = _weighted_average(applicable_rows)
        unverifiable_count = sum(1 for ev in applicable_rows if ev.unverifiable)
        out.append(
            CategoryScore(
                category=category,
                category_name=CATEGORY_NAMES_ES[category],
                weight_global=float(GLOBAL_CATEGORY_WEIGHTS[category]),
                weight_effective=float(GLOBAL_CATEGORY_WEIGHTS[category]),  # patched in aggregate_total
                score=float(score),
                criteria_count_total=totals_by_category.get(category, len(applicable_rows)),
                criteria_count_applicable=len(applicable_rows),
                criteria_count_unverifiable=unverifiable_count,
            )
        )
    return out


def _weighted_average(rows: list[CriterionEvaluation]) -> Decimal:
    total_weight = Decimal("0")
    weighted_sum = Decimal("0")
    for ev in rows:
        weight = Decimal(str(ev.weight_in_category))
        if weight <= 0:
            # Defensive: catalog constraint already enforces 0 < w <= 100.
            raise ValueError(f"criterion {ev.criterion_id} has non-positive weight {weight}")
        total_weight += weight
        weighted_sum += weight * Decimal(str(ev.score))
    if total_weight == 0:
        raise NoApplicableCriteriaError("category has no positive weights")
    return weighted_sum / total_weight


def _reject_duplicates(evaluations: list[CriterionEvaluation]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for ev in evaluations:
        if ev.criterion_id in seen:
            duplicates.append(ev.criterion_id)
        seen.add(ev.criterion_id)
    if duplicates:
        raise ValueError(f"duplicate criterion ids in aggregation input: {sorted(set(duplicates))}")


# ── CS-152 + CS-157: total aggregation with override gate ───────────────


def aggregate_total(
    evaluations: list[CriterionEvaluation],
    *,
    contract_type: str | None = None,
) -> AggregationResult:
    """Aggregate per-category scores into a single total + band.

    Steps follow RUBRICA_CONTRATO §10 1:1:

    1. Collect every ``override_triggered`` non-null across the rows
       (CS-157). Dedup, sort alphabetically for deterministic snapshots,
       and short-circuit to ``score_total=0.0`` / ``band=red`` (CS-157 AC).
    2. Compute per-category weighted averages over the *applicable*
       subset (CS-152 + CS-155).
    3. Renormalize global weights over the categories present.
    4. ``round(score_total, 1)`` with banker's rounding and assign band
       (CS-156).
    """

    overrides = _collect_overrides(evaluations)
    category_scores = compute_category_scores(evaluations, contract_type=contract_type)

    if not category_scores:
        if overrides:
            return AggregationResult(
                score_total=0.0,
                band=Band.RED,
                override_active=True,
                override_triggered=tuple(overrides),
                category_scores=(),
            )
        raise NoApplicableCriteriaError(
            "no applicable evaluations were provided; pipeline should "
            "have short-circuited with Band.NOT_ANALYZABLE upstream"
        )

    weight_sum = sum((GLOBAL_CATEGORY_WEIGHTS[c.category] for c in category_scores), Decimal("0"))
    if weight_sum <= 0:
        raise NoApplicableCriteriaError("no positive global weights in applicable categories")

    renormalized: list[CategoryScore] = []
    total = Decimal("0")
    for cs in category_scores:
        nominal = GLOBAL_CATEGORY_WEIGHTS[cs.category]
        effective = nominal / weight_sum
        contribution = effective * Decimal(str(cs.score))
        total += contribution
        renormalized.append(cs.model_copy(update={"weight_effective": float(effective)}))

    # Defensive consistency check — Σ effective ≈ 1.
    eff_sum = sum((Decimal(str(cs.weight_effective)) for cs in renormalized), Decimal("0"))
    if abs(eff_sum - Decimal("1")) > _FLOAT_TOLERANCE:
        raise AssertionError(f"effective weights drifted: sum={eff_sum}")

    rounded = banker_round_score_total(total)

    if overrides:
        return AggregationResult(
            score_total=0.0,
            band=Band.RED,
            override_active=True,
            override_triggered=tuple(overrides),
            category_scores=tuple(renormalized),
        )

    return AggregationResult(
        score_total=float(rounded),
        band=assign_band(rounded),
        override_active=False,
        override_triggered=(),
        category_scores=tuple(renormalized),
    )


def _collect_overrides(evaluations: list[CriterionEvaluation]) -> list[OverrideCode]:
    """Return the deduplicated, alphabetically-ordered override codes."""

    seen: set[OverrideCode] = set()
    for ev in evaluations:
        if ev.override_triggered is not None:
            seen.add(ev.override_triggered)
    return sorted(seen, key=lambda code: code.value)


__all__ = [
    "CATEGORY_NAMES_ES",
    "GLOBAL_CATEGORY_WEIGHTS",
    "AggregationResult",
    "NoApplicableCriteriaError",
    "aggregate_total",
    "assign_band",
    "banker_round_score_total",
    "compute_category_scores",
]
