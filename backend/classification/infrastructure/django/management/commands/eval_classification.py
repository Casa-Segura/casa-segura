"""`manage.py eval_classification` — F2 classification evaluation harness (CS-115).

Loads ``backend/fixtures/classification_eval_cases.yaml``, runs each
case through :class:`ContractClassifier` (and, for purchase types,
:class:`LeasingReclassificationDetector`), and emits:

* a per-type accuracy table to stdout,
* NOT_CLASSIFIABLE precision/recall,
* a reclassification confusion matrix limited to the
  ``{CVC, CVP, APV} → {CVC, CVP, APV, LEA}`` subset (PRD F2 BR-02), and
* an optional JSON dump on disk for CI artifacts.

The command is **safe to run repeatedly**: it has no side effects on the
database, on Celery, or on any external systems other than OpenRouter.
It exits non-zero when macro accuracy drops below ``--threshold``, which
is the hook the future CI gate (CS-115 AC4) will use; today the gate is
documented but not wired into pipelines.

Modes
-----
* default — calls OpenRouter for every case. Slow, costs money. Manual.
* ``--dry-run`` — validates the YAML schema and prints the coverage
  matrix without making any LLM call. Use this in CI today.

The harness intentionally **does not** mock the LLM. CS-115 reserves the
right to swap in a deterministic fake by injecting ``ContractClassifier``
through a constructor later; pytest-level mocking is deferred per the
ticket's "no Python unit tests in this slice" constraint.

Usage::

    python manage.py eval_classification --dry-run
    python manage.py eval_classification --threshold 0.95 --out artifacts/eval.json
    python manage.py eval_classification --fixture path/to/cases.yaml
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from classification.application.classifier import (
    ClassificationError,
    ContractClassifier,
)
from classification.application.leasing_detector import (
    LeasingReclassificationDetector,
)
from classification.domain.contract_type import ContractType


DEFAULT_FIXTURE = "fixtures/classification_eval_cases.yaml"

# Purchase types that trigger the leasing reclassification pass per
# PRD F2 BR-02 / US-03 (and the detector's APPLICABLE_INITIAL_TYPES).
PURCHASE_TYPES: frozenset[ContractType] = frozenset(
    {ContractType.CVC, ContractType.CVP, ContractType.APV}
)


# ---------------------------------------------------------------------------
# Pydantic v2 schemas — strict YAML validation.
# ---------------------------------------------------------------------------


class _ExpectedLeasing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_count: int = Field(ge=0, le=6)
    expected_recommendation: ContractType


class _Expected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contract_type: ContractType
    min_confidence: float = Field(ge=0.0, le=1.0)
    leasing_indicators: _ExpectedLeasing | None = None


class _Case(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    contract_type: ContractType
    description: str = Field(min_length=1)
    contract_text: str = Field(min_length=1)
    expected: _Expected
    tags: list[str] = Field(default_factory=list)


class _Thresholds(BaseModel):
    model_config = ConfigDict(extra="forbid")

    macro_accuracy_min: float = Field(ge=0.0, le=1.0)
    not_classifiable_precision_min: float = Field(ge=0.0, le=1.0)
    reclassification_false_positive_max: float = Field(ge=0.0, le=1.0)
    reclassification_false_negative_max: float = Field(ge=0.0, le=1.0)


class _Fixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thresholds: _Thresholds
    cases: list[_Case] = Field(min_length=1)


# ---------------------------------------------------------------------------
# In-memory result envelopes (plain dataclasses; not part of the domain layer).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CaseOutcome:
    case_id: str
    expected_type: ContractType
    predicted_type: ContractType
    predicted_confidence: float
    leasing_expected_count: int | None
    leasing_observed_count: int | None
    leasing_expected_recommendation: ContractType | None
    leasing_observed_recommendation: ContractType | None
    error: str | None


@dataclass
class _Metrics:
    total: int = 0
    correct: int = 0
    per_type_correct: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    per_type_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    not_classifiable_tp: int = 0
    not_classifiable_fp: int = 0
    not_classifiable_fn: int = 0
    reclassification_matrix: dict[str, Counter[str]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    reclassification_fp: int = 0  # purchase incorrectly recommended LEA
    reclassification_fn: int = 0  # disguised leasing missed (expected LEA, got purchase)
    reclassification_total_purchase: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)

    def macro_accuracy(self) -> float:
        if self.total == 0:
            return 0.0
        return self.correct / self.total

    def not_classifiable_precision(self) -> float | None:
        denom = self.not_classifiable_tp + self.not_classifiable_fp
        if denom == 0:
            return None
        return self.not_classifiable_tp / denom

    def not_classifiable_recall(self) -> float | None:
        denom = self.not_classifiable_tp + self.not_classifiable_fn
        if denom == 0:
            return None
        return self.not_classifiable_tp / denom

    def reclassification_fp_rate(self) -> float | None:
        if self.reclassification_total_purchase == 0:
            return None
        return self.reclassification_fp / self.reclassification_total_purchase

    def reclassification_fn_rate(self) -> float | None:
        if self.reclassification_total_purchase == 0:
            return None
        return self.reclassification_fn / self.reclassification_total_purchase


# ---------------------------------------------------------------------------
# Command.
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Evaluate ContractClassifier + LeasingReclassificationDetector against "
        "the curated CS-115 fixture corpus. Use --dry-run to validate the "
        "YAML schema and report coverage without spending OpenRouter credit."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--fixture",
            default=None,
            dest="fixture",
            help=(
                "Path to the YAML fixture. Defaults to "
                "<BASE_DIR>/fixtures/classification_eval_cases.yaml."
            ),
        )
        parser.add_argument(
            "--out",
            default=None,
            dest="out",
            help="Optional path to write the full metrics report as JSON.",
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=None,
            dest="threshold",
            help=(
                "Macro-accuracy floor; the command exits non-zero when "
                "observed accuracy falls below this value. Defaults to the "
                "fixture's thresholds.macro_accuracy_min."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help=(
                "Validate the YAML schema and print the coverage matrix "
                "without invoking the LLM. Safe for CI."
            ),
        )

    # ------------------------------------------------------------------
    # handle
    # ------------------------------------------------------------------
    def handle(self, *args: Any, **opts: Any) -> None:
        fixture_path = self._resolve_fixture_path(opts.get("fixture"))
        if not fixture_path.exists():
            raise CommandError(f"Fixture not found: {fixture_path}")

        fixture = self._load_and_validate(fixture_path)
        threshold = opts.get("threshold")
        if threshold is None:
            threshold = fixture.thresholds.macro_accuracy_min

        if opts.get("dry_run"):
            self._print_coverage(fixture)
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDry-run OK: {len(fixture.cases)} cases validated; "
                    "no LLM calls made."
                )
            )
            return

        outcomes = self._run_cases(fixture)
        metrics = self._aggregate(outcomes)
        self._print_report(metrics, threshold=threshold)

        out_path: str | None = opts.get("out")
        if out_path:
            self._write_json(metrics, outcomes, Path(out_path))

        observed = metrics.macro_accuracy()
        if observed < threshold:
            self.stderr.write(
                self.style.ERROR(
                    f"FAIL: macro accuracy {observed:.4f} below threshold {threshold:.4f}"
                )
            )
            sys.exit(1)

    # ------------------------------------------------------------------
    # Fixture loading / validation
    # ------------------------------------------------------------------
    def _resolve_fixture_path(self, fixture_arg: str | None) -> Path:
        if fixture_arg:
            return Path(fixture_arg).expanduser().resolve()
        return (Path(settings.BASE_DIR) / DEFAULT_FIXTURE).resolve()

    def _load_and_validate(self, path: Path) -> _Fixture:
        try:
            with path.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError as exc:
            raise CommandError(f"Invalid YAML at {path}: {exc}") from exc

        if not isinstance(data, dict):
            raise CommandError(
                f"{path}: expected top-level mapping, got {type(data).__name__}"
            )

        try:
            fixture = _Fixture.model_validate(data)
        except ValidationError as exc:
            raise CommandError(f"{path}: schema violation\n{exc}") from exc

        # Defensive: enforce unique IDs (pydantic does not).
        seen: set[str] = set()
        for case in fixture.cases:
            if case.id in seen:
                raise CommandError(f"{path}: duplicate case id {case.id!r}")
            seen.add(case.id)

            # Leasing indicators only make sense for purchase types
            # (PRD F2 BR-02: detector skips ARV/ARC/IVU/FSV/LEA/NOT_CLASSIFIABLE).
            if case.expected.leasing_indicators is not None:
                if case.expected.contract_type not in PURCHASE_TYPES:
                    raise CommandError(
                        f"{path}: case {case.id!r} declares leasing_indicators "
                        f"but expected contract_type {case.expected.contract_type.value} "
                        f"is not a purchase type (CVC/CVP/APV)."
                    )

        return fixture

    # ------------------------------------------------------------------
    # Coverage matrix (dry-run output)
    # ------------------------------------------------------------------
    def _print_coverage(self, fixture: _Fixture) -> None:
        counts: Counter[str] = Counter()
        for case in fixture.cases:
            counts[case.contract_type.value] += 1

        self.stdout.write(self.style.MIGRATE_HEADING("Coverage matrix"))
        for ct in ContractType:
            n = counts.get(ct.value, 0)
            line = f"  {ct.value:<18} {n:>3}"
            if ct in PURCHASE_TYPES | {ContractType.ARV, ContractType.ARC,
                                         ContractType.LEA, ContractType.IVU,
                                         ContractType.FSV}:
                # The eight covered types must each have ≥3 fixtures (AC1).
                marker = "OK" if n >= 3 else "FAIL (need ≥3)"
                line += f"   {marker}"
            elif ct is ContractType.NOT_CLASSIFIABLE:
                marker = "OK" if n >= 4 else "FAIL (need ≥4)"
                line += f"   {marker}"
            self.stdout.write(line)

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\nTotal cases: {len(fixture.cases)} (CS-115 AC2 requires ≥20)"
            )
        )
        self.stdout.write("\nThresholds (PRD F2 §9):")
        for name, value in fixture.thresholds.model_dump().items():
            self.stdout.write(f"  {name:<40} {value}")

    # ------------------------------------------------------------------
    # LLM invocation (live mode)
    # ------------------------------------------------------------------
    def _run_cases(self, fixture: _Fixture) -> list[_CaseOutcome]:
        outcomes: list[_CaseOutcome] = []
        # Use a single classifier + detector to share the underlying
        # HTTPX pool — both close cleanly on context exit.
        with ContractClassifier() as classifier, LeasingReclassificationDetector() as detector:
            for case in fixture.cases:
                outcomes.append(self._run_one(case, classifier, detector))
        return outcomes

    def _run_one(
        self,
        case: _Case,
        classifier: ContractClassifier,
        detector: LeasingReclassificationDetector,
    ) -> _CaseOutcome:
        try:
            result = classifier.classify(case.contract_text)
        except ClassificationError as exc:
            return _CaseOutcome(
                case_id=case.id,
                expected_type=case.expected.contract_type,
                predicted_type=ContractType.NOT_CLASSIFIABLE,
                predicted_confidence=0.0,
                leasing_expected_count=(
                    case.expected.leasing_indicators.expected_count
                    if case.expected.leasing_indicators
                    else None
                ),
                leasing_observed_count=None,
                leasing_expected_recommendation=(
                    case.expected.leasing_indicators.expected_recommendation
                    if case.expected.leasing_indicators
                    else None
                ),
                leasing_observed_recommendation=None,
                error=f"{exc.code or 'ERR'}: {exc}",
            )

        leasing_observed_count: int | None = None
        leasing_observed_rec: ContractType | None = None
        if result.contract_type in PURCHASE_TYPES:
            try:
                reclassification = detector.detect(
                    case.contract_text,
                    initial_type=result.contract_type,
                )
                leasing_observed_count = reclassification.indicators.total_indicators_found
                leasing_observed_rec = reclassification.recommended_type
            except ClassificationError as exc:
                return _CaseOutcome(
                    case_id=case.id,
                    expected_type=case.expected.contract_type,
                    predicted_type=result.contract_type,
                    predicted_confidence=result.confidence,
                    leasing_expected_count=(
                        case.expected.leasing_indicators.expected_count
                        if case.expected.leasing_indicators
                        else None
                    ),
                    leasing_observed_count=None,
                    leasing_expected_recommendation=(
                        case.expected.leasing_indicators.expected_recommendation
                        if case.expected.leasing_indicators
                        else None
                    ),
                    leasing_observed_recommendation=None,
                    error=f"leasing_detector {exc.code or 'ERR'}: {exc}",
                )

        return _CaseOutcome(
            case_id=case.id,
            expected_type=case.expected.contract_type,
            predicted_type=result.contract_type,
            predicted_confidence=result.confidence,
            leasing_expected_count=(
                case.expected.leasing_indicators.expected_count
                if case.expected.leasing_indicators
                else None
            ),
            leasing_observed_count=leasing_observed_count,
            leasing_expected_recommendation=(
                case.expected.leasing_indicators.expected_recommendation
                if case.expected.leasing_indicators
                else None
            ),
            leasing_observed_recommendation=leasing_observed_rec,
            error=None,
        )

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------
    def _aggregate(self, outcomes: list[_CaseOutcome]) -> _Metrics:
        metrics = _Metrics()
        for o in outcomes:
            metrics.total += 1
            metrics.per_type_total[o.expected_type.value] += 1

            if o.error is not None:
                metrics.errors.append((o.case_id, o.error))

            # Final type (after reclassification, when one was attempted).
            final_predicted = o.leasing_observed_recommendation or o.predicted_type
            final_expected = o.leasing_expected_recommendation or o.expected_type

            if final_predicted == final_expected:
                metrics.correct += 1
                metrics.per_type_correct[o.expected_type.value] += 1

            # NOT_CLASSIFIABLE precision/recall.
            if final_expected is ContractType.NOT_CLASSIFIABLE:
                if final_predicted is ContractType.NOT_CLASSIFIABLE:
                    metrics.not_classifiable_tp += 1
                else:
                    metrics.not_classifiable_fn += 1
            elif final_predicted is ContractType.NOT_CLASSIFIABLE:
                metrics.not_classifiable_fp += 1

            # Reclassification confusion: only over fixtures whose expected
            # FIRST-PASS type is a purchase type. For those we count:
            #  - FP: expected purchase, got LEA
            #  - FN: expected LEA, got purchase (only meaningful if expected is LEA;
            #        we encode that via the leasing_expected_recommendation field).
            if o.expected_type in PURCHASE_TYPES and o.leasing_expected_recommendation is not None:
                metrics.reclassification_total_purchase += 1
                row = o.leasing_expected_recommendation.value
                col = (o.leasing_observed_recommendation or o.predicted_type).value
                metrics.reclassification_matrix[row][col] += 1

                expected_lea = o.leasing_expected_recommendation is ContractType.LEA
                observed_lea = (
                    o.leasing_observed_recommendation is ContractType.LEA
                )
                if not expected_lea and observed_lea:
                    metrics.reclassification_fp += 1
                if expected_lea and not observed_lea:
                    metrics.reclassification_fn += 1

        return metrics

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------
    def _print_report(self, metrics: _Metrics, *, threshold: float) -> None:
        self.stdout.write(self.style.MIGRATE_HEADING("Per-type accuracy"))
        for ct in ContractType:
            total = metrics.per_type_total.get(ct.value, 0)
            if total == 0:
                continue
            hits = metrics.per_type_correct.get(ct.value, 0)
            pct = hits / total if total else 0.0
            self.stdout.write(
                f"  {ct.value:<18} {hits:>3} / {total:<3}  ({pct:.2%})"
            )

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\nMacro accuracy: {metrics.macro_accuracy():.4f} "
                f"(threshold {threshold:.4f})"
            )
        )

        nc_prec = metrics.not_classifiable_precision()
        nc_rec = metrics.not_classifiable_recall()
        self.stdout.write("\nNOT_CLASSIFIABLE:")
        self.stdout.write(
            f"  precision: {nc_prec if nc_prec is None else f'{nc_prec:.4f}'}"
        )
        self.stdout.write(
            f"  recall:    {nc_rec if nc_rec is None else f'{nc_rec:.4f}'}"
        )

        self.stdout.write(
            self.style.MIGRATE_HEADING("\nReclassification confusion (purchase → final)")
        )
        if metrics.reclassification_total_purchase == 0:
            self.stdout.write("  (no purchase cases declared leasing expectations)")
        else:
            cols = ["CVC", "CVP", "APV", "LEA"]
            header = "  expected\\got    " + "  ".join(f"{c:>5}" for c in cols)
            self.stdout.write(header)
            for row in ["CVC", "CVP", "APV", "LEA"]:
                counts = metrics.reclassification_matrix.get(row, Counter())
                line = f"  {row:<14}" + "  ".join(
                    f"{counts.get(col, 0):>5}" for col in cols
                )
                self.stdout.write(line)
            fp = metrics.reclassification_fp_rate()
            fn = metrics.reclassification_fn_rate()
            self.stdout.write(
                f"\n  FP rate (purchase→LEA wrongly): "
                f"{fp if fp is None else f'{fp:.4f}'}"
            )
            self.stdout.write(
                f"  FN rate (LEA missed as purchase): "
                f"{fn if fn is None else f'{fn:.4f}'}"
            )

        if metrics.errors:
            self.stdout.write(self.style.WARNING("\nErrors:"))
            for case_id, err in metrics.errors:
                self.stdout.write(f"  {case_id}: {err}")

    def _write_json(
        self,
        metrics: _Metrics,
        outcomes: list[_CaseOutcome],
        path: Path,
    ) -> None:
        payload: dict[str, Any] = {
            "summary": {
                "total": metrics.total,
                "correct": metrics.correct,
                "macro_accuracy": metrics.macro_accuracy(),
                "not_classifiable": {
                    "precision": metrics.not_classifiable_precision(),
                    "recall": metrics.not_classifiable_recall(),
                    "tp": metrics.not_classifiable_tp,
                    "fp": metrics.not_classifiable_fp,
                    "fn": metrics.not_classifiable_fn,
                },
                "reclassification": {
                    "total_purchase_cases": metrics.reclassification_total_purchase,
                    "false_positive_rate": metrics.reclassification_fp_rate(),
                    "false_negative_rate": metrics.reclassification_fn_rate(),
                    "matrix": {
                        row: dict(counts)
                        for row, counts in metrics.reclassification_matrix.items()
                    },
                },
            },
            "per_type": {
                ct: {
                    "total": metrics.per_type_total[ct],
                    "correct": metrics.per_type_correct.get(ct, 0),
                }
                for ct in metrics.per_type_total
            },
            "outcomes": [
                {
                    "case_id": o.case_id,
                    "expected_type": o.expected_type.value,
                    "predicted_type": o.predicted_type.value,
                    "predicted_confidence": o.predicted_confidence,
                    "leasing_expected_count": o.leasing_expected_count,
                    "leasing_observed_count": o.leasing_observed_count,
                    "leasing_expected_recommendation": (
                        o.leasing_expected_recommendation.value
                        if o.leasing_expected_recommendation
                        else None
                    ),
                    "leasing_observed_recommendation": (
                        o.leasing_observed_recommendation.value
                        if o.leasing_observed_recommendation
                        else None
                    ),
                    "error": o.error,
                }
                for o in outcomes
            ],
            "errors": [{"case_id": cid, "error": err} for cid, err in metrics.errors],
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"\nWrote JSON report to {path}"))
