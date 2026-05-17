"""Leasing reclassification detector service (CS-111).

Second pass after CS-110's primary classification. Given the contract
text and the type CS-110 produced, this service:

1. **Skips** when the initial type is not in
   ``APPLICABLE_INITIAL_TYPES`` (``{CVC, CVP, APV}`` per PRD F2 BR-02 /
   US-03). Returns a zero-indicator "keep original" result so the
   orchestrator can treat the skip path uniformly.
2. Otherwise issues one deterministic OpenRouter chat-completion call
   against :mod:`classification.application.leasing_prompts`.
3. Validates the JSON into :class:`LeasingIndicators` and wraps the
   recommendation in :class:`LeasingReclassificationResult`.

The service is intentionally narrow: it **does not** mutate the
upstream :class:`~classification.domain.dtos.ClassificationResult`. The
orchestrator (CS-112+) reads ``should_reclassify`` and decides whether
to persist ``contract_type = LEA`` per PRD US-03.

Call shape mirrors CS-110's ``ContractClassifier``: ``temperature=0.1``,
``response_format={"type": "json_object"}``, code-fence strip, and
typed :class:`ClassificationError` on parse/transport failures (reuses
CS-110's exception type so callers map errors uniformly).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Final

from pydantic import ValidationError

from classification.application.classifier import ClassificationError
from classification.application.leasing_prompts import (
    APPLICABLE_INITIAL_TYPES,
    build_messages,
)
from classification.domain.contract_type import ContractType
from classification.domain.leasing_indicators import (
    DEFAULT_RECLASSIFICATION_THRESHOLD,
    LeasingIndicators,
)
from classification.domain.reclassification import LeasingReclassificationResult
from shared.llm.openrouter import (
    ChatCompletionResult,
    OpenRouterClient,
    OpenRouterError,
)

logger = logging.getLogger(__name__)


DEFAULT_LEASING_MODEL: Final[str] = "anthropic/claude-sonnet-4"
"""Aligned with ``LLM_CLASSIFICATION_MODEL`` default in PRD F2 §6.3."""

DEFAULT_TEMPERATURE: Final[float] = 0.1
"""Deterministic-but-not-frozen sampling per PRD F2 §6.3."""


_JSON_FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*```(?:json)?\s*|\s*```\s*$",
    flags=re.IGNORECASE,
)


def _skip_result(initial_type: ContractType) -> LeasingReclassificationResult:
    """Build the canonical 'no reclassification' envelope for the skip path.

    Used both when ``initial_type`` is outside ``APPLICABLE_INITIAL_TYPES``
    and as the shape returned when the LLM reports zero indicators.
    """
    return LeasingReclassificationResult(
        original_type=initial_type,
        recommended_type=initial_type,
        should_reclassify=False,
        indicators=LeasingIndicators(),
        confidence=0.0,
        reasoning=None,
    )


class LeasingReclassificationDetector:
    """Second-pass detector that recommends ``LEA`` reclassification.

    The client is injected so tests (deferred to CS-115) and orchestrators
    can plug in mocks or share a single HTTPX connection pool with the
    CS-110 classifier.
    """

    def __init__(
        self,
        *,
        client: OpenRouterClient | None = None,
        model: str = DEFAULT_LEASING_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        threshold: int = DEFAULT_RECLASSIFICATION_THRESHOLD,
    ) -> None:
        self._client = client or OpenRouterClient()
        self._owns_client = client is None
        self._model = model
        self._temperature = temperature
        self._threshold = threshold

    def __enter__(self) -> LeasingReclassificationDetector:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def detect(
        self,
        extracted_text: str,
        initial_type: ContractType,
    ) -> LeasingReclassificationResult:
        """Run a single leasing-detection pass over ``extracted_text``.

        Skips (returns the canonical "keep original" envelope) when
        ``initial_type`` is not in ``APPLICABLE_INITIAL_TYPES``
        (PRD F2 BR-02 / US-03 AC1).

        :raises ClassificationError: if the LLM call fails after the
            shared client's retry budget, or if the response cannot be
            parsed into a :class:`LeasingIndicators` payload.
        """
        # Skip path: ARV/ARC/IVU/FSV/LEA/NOT_CLASSIFIABLE all bypass the
        # detector with zero side effects. Logged at info level so the
        # decision is auditable without polluting warning streams.
        if initial_type not in APPLICABLE_INITIAL_TYPES:
            logger.info(
                "leasing_detector.skipped",
                extra={"initial_type": initial_type.value},
            )
            return _skip_result(initial_type)

        if not extracted_text or not extracted_text.strip():
            raise ClassificationError(
                "extracted_text is empty",
                code="EMPTY_INPUT",
            )

        messages = build_messages(
            extracted_text=extracted_text,
            initial_type=initial_type,
        )

        try:
            completion = self._client.chat_completion(
                model=self._model,
                messages=messages,
                extra_body={
                    "temperature": self._temperature,
                    "response_format": {"type": "json_object"},
                },
            )
        except OpenRouterError as exc:
            logger.warning(
                "leasing_detector.openrouter_error",
                extra={
                    "model": self._model,
                    "status_code": exc.status_code,
                    "initial_type": initial_type.value,
                },
            )
            raise ClassificationError(
                f"OpenRouter call failed: {exc}",
                code="LLM_TRANSIENT_FAILURE",
            ) from exc

        return self._parse(completion, initial_type=initial_type)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _parse(
        self,
        completion: ChatCompletionResult,
        *,
        initial_type: ContractType,
    ) -> LeasingReclassificationResult:
        raw = (completion.content or "").strip()
        cleaned = _JSON_FENCE_RE.sub("", raw).strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(
                "leasing_detector.parse_failed",
                extra={"model": self._model, "error": str(exc)},
            )
            raise ClassificationError(
                "LLM returned non-JSON content",
                code="LLM_PARSE_FAILED",
            ) from exc

        if not isinstance(payload, dict):
            logger.warning(
                "leasing_detector.parse_failed",
                extra={"model": self._model, "error": "payload is not an object"},
            )
            raise ClassificationError(
                "LLM JSON payload is not an object",
                code="LLM_PARSE_FAILED",
            )

        try:
            indicators = self._extract_indicators(payload)
        except ValidationError as exc:
            logger.warning(
                "leasing_detector.schema_violation",
                extra={"model": self._model, "error": str(exc)},
            )
            raise ClassificationError(
                "LLM JSON did not match LeasingIndicators schema",
                code="LLM_PARSE_FAILED",
            ) from exc

        confidence = _coerce_confidence(payload.get("confidence"))
        reasoning = _coerce_reasoning(payload.get("reasoning"))

        # The detector — not the LLM — owns the reclassification decision.
        # We deliberately ignore any ``should_reclassify`` the model
        # returned: the legal-product hinge (4-of-6) is in our threshold
        # constant, not in the prompt's interpretation.
        should_reclassify = indicators.is_leasing(threshold=self._threshold)
        recommended_type = ContractType.LEA if should_reclassify else initial_type

        try:
            return LeasingReclassificationResult(
                original_type=initial_type,
                recommended_type=recommended_type,
                should_reclassify=should_reclassify,
                indicators=indicators,
                confidence=confidence,
                reasoning=reasoning,
            )
        except ValidationError as exc:
            logger.warning(
                "leasing_detector.envelope_invalid",
                extra={"model": self._model, "error": str(exc)},
            )
            raise ClassificationError(
                "LLM JSON did not match LeasingReclassificationResult schema",
                code="LLM_PARSE_FAILED",
            ) from exc

    @staticmethod
    def _extract_indicators(payload: dict[str, Any]) -> LeasingIndicators:
        """Build :class:`LeasingIndicators` from either flat or nested JSON.

        The prompt asks for a flat object, but PRD §8.4's reference
        shape nests the six flags under ``leasing_indicators``. Accept
        both so a prompt drift in either direction does not break the
        parser.
        """
        nested = payload.get("leasing_indicators")
        source: dict[str, Any]
        if isinstance(nested, dict):
            source = nested
        else:
            source = payload

        indicator_kwargs: dict[str, bool] = {}
        for field in LeasingIndicators.model_fields:
            value = source.get(field)
            if isinstance(value, dict):
                # PRD §8.4 nested shape: {"detected": bool, "evidence": ...}.
                detected = value.get("detected", False)
                indicator_kwargs[field] = bool(detected)
            else:
                indicator_kwargs[field] = bool(value) if value is not None else False
        return LeasingIndicators(**indicator_kwargs)


def _coerce_confidence(value: Any) -> float:
    """Clamp ``value`` into ``[0.0, 1.0]``; default to ``0.0`` if missing.

    Out-of-range or non-numeric values are clamped rather than rejected
    so a single LLM hiccup does not poison the detector — the
    confidence is advisory; the indicator booleans drive the decision.
    """
    if value is None:
        return 0.0
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


def _coerce_reasoning(value: Any) -> str | None:
    """Return a trimmed string for ``reasoning`` or ``None``."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


__all__ = [
    "DEFAULT_LEASING_MODEL",
    "DEFAULT_TEMPERATURE",
    "LeasingReclassificationDetector",
]
