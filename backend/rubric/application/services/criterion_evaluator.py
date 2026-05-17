"""Criterion evaluator framework (CS-158).

Defines:

* ``EvaluationContext`` — the bundle every evaluator consumes (contract
  text, classification, ``EconomicSummary``, elements detected).
* ``CriterionEvaluator`` protocol — the interface implementations register
  against.
* ``CriterionRegistry`` — id → callable map with collision detection.
* ``Dispatcher`` — async dispatcher with concurrency cap **8**, per-call
  timeout **30 s** (PRD_F4 US-01/BR-08), and one retry. Failures collapse
  to unverifiable rows via ``unverifiable.unverifiable_row``.

The dispatcher is intentionally framework-agnostic about LLM transport:
evaluators receive whatever helper their category module needs (LLM
client, pattern matcher, deterministic short-circuit) — the framework
only enforces the *contract* and the SLO.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from rubric.application.services.unverifiable import UnverifiableReason, unverifiable_row
from rubric.domain.entities import CriterionEvaluation

logger = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = 8
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 1  # one retry → up to two attempts total (PRD_F4 US-01)
DEFAULT_HARD_TIMEOUT_SECONDS = 60.0  # whole-engine budget (PRD_F4 BR-09)


@dataclass(frozen=True)
class CriterionSpec:
    """The slice of the rubric catalog the dispatcher uses at runtime.

    Mirrors ``rubric.infrastructure.django.models.Criterion`` but lives in
    ``application`` so tests don't need a DB.
    """

    criterion_id: str
    category: str
    weight_in_category: float
    applicable_types: tuple[str, ...]
    legal_anchor: tuple[str, ...]
    override_code: str | None
    evaluation_prompt: str
    scoring_scale: dict[str, str]
    worst_case_when_unverifiable: float
    depends_on_economic: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationContext:
    """Shared per-analysis context handed to every evaluator."""

    analysis_id: str
    contract_text: str
    contract_type: str
    elements_detected: dict[str, Any] = field(default_factory=dict)
    economic_summary: dict[str, Any] = field(default_factory=dict)
    classification: dict[str, Any] = field(default_factory=dict)
    benchmark_version: str | None = None
    corpus_version: str | None = None
    rubric_version: str = "1.0.0"


EvaluatorCallable = Callable[[CriterionSpec, EvaluationContext], Awaitable[CriterionEvaluation]]


class CriterionEvaluator(Protocol):
    """Async callable: ``(spec, context) -> CriterionEvaluation``."""

    async def __call__(
        self,
        spec: CriterionSpec,
        context: EvaluationContext,
    ) -> CriterionEvaluation: ...  # pragma: no cover — protocol


class DuplicateRegistrationError(ValueError):
    """Raised when two evaluators are registered for the same criterion id."""


class MissingEvaluatorError(LookupError):
    """Raised when the dispatcher cannot find an evaluator for a criterion id."""


class CriterionRegistry:
    """Per-rubric-version id → evaluator map.

    The registry refuses duplicate registrations (CS-158 AC: startup
    health check fails fast on unknown criterion_id) and exposes a
    ``health_check`` that compares the registered ids with the catalog
    rows the dispatcher is about to invoke.
    """

    def __init__(self) -> None:
        self._evaluators: dict[str, EvaluatorCallable] = {}

    def register(self, criterion_id: str, evaluator: EvaluatorCallable) -> None:
        if criterion_id in self._evaluators:
            raise DuplicateRegistrationError(f"evaluator already registered for criterion {criterion_id!r}")
        self._evaluators[criterion_id] = evaluator

    def unregister(self, criterion_id: str) -> None:
        self._evaluators.pop(criterion_id, None)

    def get(self, criterion_id: str) -> EvaluatorCallable:
        try:
            return self._evaluators[criterion_id]
        except KeyError as exc:
            raise MissingEvaluatorError(f"no evaluator registered for criterion {criterion_id!r}") from exc

    def __contains__(self, criterion_id: str) -> bool:
        return criterion_id in self._evaluators

    def __len__(self) -> int:
        return len(self._evaluators)

    def ids(self) -> set[str]:
        return set(self._evaluators.keys())

    def health_check(self, expected_ids: set[str]) -> None:
        missing = expected_ids - self.ids()
        if missing:
            raise MissingEvaluatorError(f"registry is missing evaluators for: {sorted(missing)}")


@dataclass
class DispatchStats:
    """Lightweight telemetry surface — promoted to Prometheus in F4 metrics."""

    started: int = 0
    completed: int = 0
    unverifiable: int = 0
    timeouts: int = 0
    parse_failures: int = 0
    max_concurrency_seen: int = 0
    total_elapsed_ms: int = 0


class CriterionDispatcher:
    """Evaluate criteria in parallel with a hard concurrency cap.

    The dispatcher is the only place that converts evaluator failures
    into ``unverifiable`` rows — every evaluator stays single-purpose
    and may raise freely.
    """

    def __init__(
        self,
        registry: CriterionRegistry,
        *,
        concurrency: int = DEFAULT_CONCURRENCY,
        per_call_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        hard_timeout_seconds: float = DEFAULT_HARD_TIMEOUT_SECONDS,
    ) -> None:
        if concurrency <= 0:
            raise ValueError("concurrency must be > 0")
        self.registry = registry
        self.concurrency = concurrency
        self.per_call_timeout_seconds = per_call_timeout_seconds
        self.max_retries = max_retries
        self.hard_timeout_seconds = hard_timeout_seconds
        self.stats = DispatchStats()

    async def evaluate_all(
        self,
        specs: list[CriterionSpec],
        context: EvaluationContext,
    ) -> list[CriterionEvaluation]:
        """Run all evaluators applicable to ``context.contract_type``.

        Non-applicable rows are emitted with ``applicable=False`` so the
        caller can preserve the per-category ``criteria_count_total``
        denominator in ``CategoryScore`` (CS-155 AC).
        """

        semaphore = asyncio.Semaphore(self.concurrency)
        active_counter = {"count": 0}
        start = time.perf_counter()

        async def _run(spec: CriterionSpec) -> CriterionEvaluation:
            if context.contract_type not in spec.applicable_types:
                # CS-155: non-applicable rows are returned but not counted.
                return _non_applicable_row(spec)

            evaluator = self.registry.get(spec.criterion_id)
            self.stats.started += 1

            async with semaphore:
                active_counter["count"] += 1
                self.stats.max_concurrency_seen = max(self.stats.max_concurrency_seen, active_counter["count"])
                try:
                    result = await self._invoke_with_retry(evaluator, spec, context)
                finally:
                    active_counter["count"] -= 1
            self.stats.completed += 1
            if result.unverifiable:
                self.stats.unverifiable += 1
            return result

        tasks = [asyncio.create_task(_run(spec)) for spec in specs]
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=False),
                timeout=self.hard_timeout_seconds,
            )
        except TimeoutError:
            for task in tasks:
                task.cancel()
            raise

        self.stats.total_elapsed_ms = int((time.perf_counter() - start) * 1000)
        return list(results)

    async def _invoke_with_retry(
        self,
        evaluator: EvaluatorCallable,
        spec: CriterionSpec,
        context: EvaluationContext,
    ) -> CriterionEvaluation:
        attempts = self.max_retries + 1
        last_exc: BaseException | None = None
        for attempt in range(1, attempts + 1):
            try:
                return await asyncio.wait_for(
                    evaluator(spec, context),
                    timeout=self.per_call_timeout_seconds,
                )
            except TimeoutError as exc:
                self.stats.timeouts += 1
                last_exc = exc
                logger.warning(
                    "rubric.criterion.timeout",
                    extra={
                        "criterion_id": spec.criterion_id,
                        "attempt": attempt,
                    },
                )
            except (ValueError, KeyError, TypeError) as exc:  # JSON / parse / contract failure
                self.stats.parse_failures += 1
                last_exc = exc
                logger.warning(
                    "rubric.criterion.parse_failed",
                    extra={"criterion_id": spec.criterion_id, "attempt": attempt, "err": str(exc)},
                )
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "rubric.criterion.error",
                    extra={"criterion_id": spec.criterion_id, "attempt": attempt, "err": str(exc)},
                )

        reason = (
            UnverifiableReason.TIMEOUT
            if isinstance(last_exc, asyncio.TimeoutError)
            else UnverifiableReason.LLM_FAILURE_AFTER_RETRY
        )
        return unverifiable_row(
            criterion_id=spec.criterion_id,
            category=spec.category,
            weight_in_category=spec.weight_in_category,
            worst_case_score=spec.worst_case_when_unverifiable,
            reason=reason,
            justification=(
                f"Evaluation for {spec.criterion_id} failed after {attempts} attempts "
                f"({type(last_exc).__name__ if last_exc else 'unknown'})."
            ),
        )


def _non_applicable_row(spec: CriterionSpec) -> CriterionEvaluation:
    """Emit a placeholder row for a non-applicable criterion (CS-155).

    These rows never enter category aggregation but preserve the
    ``criteria_count_total`` denominator the report displays.
    """

    return CriterionEvaluation(
        criterion_id=spec.criterion_id,
        category=spec.category,  # type: ignore[arg-type]
        applicable=False,
        evaluated=False,
        unverifiable=False,
        score=0.0,
        weight_in_category=spec.weight_in_category,
        override_triggered=None,
        justification=(f"Criterion {spec.criterion_id} does not apply to contract type " f"{spec.applicable_types}."),
        evidence_snippet=None,
    )


__all__ = [
    "DEFAULT_CONCURRENCY",
    "DEFAULT_HARD_TIMEOUT_SECONDS",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT_SECONDS",
    "CriterionDispatcher",
    "CriterionEvaluator",
    "CriterionRegistry",
    "CriterionSpec",
    "DispatchStats",
    "DuplicateRegistrationError",
    "EvaluationContext",
    "EvaluatorCallable",
    "MissingEvaluatorError",
]
