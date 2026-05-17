"""Contract classification service (CS-110).

Orchestrates OpenRouter chat-completion calls against the prompts in
:mod:`classification.application.prompts` and returns a validated
:class:`~classification.domain.dtos.ClassificationResult`. The service
implements the PRD F2 §US-01 confidence-band protocol:

    * ``confidence > 0.85`` → accept the primary call (``attempts=1``).
    * ``0.65 ≤ confidence ≤ 0.85`` → run the §8.3 validation prompt.
        * Validator agrees on ``contract_type`` AND its own confidence is
          ``> 0.65`` → accept the validator's reading (``attempts=2``).
        * Otherwise → return ``NOT_CLASSIFIABLE`` (``attempts=2``).
    * ``confidence < 0.65`` → return ``NOT_CLASSIFIABLE`` (``attempts=1``).

Design notes:

* Deterministic generation (``temperature=0.1`` matching PRD F2 §6.3
  default ``LLM_TEMPERATURE``).
* Defensive parsing: strip code fences and surface a typed
  ``ClassificationError`` rather than a raw stack trace.
* ``NOT_CLASSIFIABLE`` is a *legitimate* outcome (PRD §US-06). It is
  distinct from ``ClassificationError(LLM_PARSE_FAILED)``, which means
  the LLM returned garbage and the upstream submission must be marked
  ``failed_classification`` instead of presented to the user.
* When the validator overrides the primary type, the persisted envelope
  uses the validator's confidence (more honest signal — second pass with
  full prior context); see ``_apply_validator``.

The service stays in the application layer: it depends on the domain
DTO/enum and on the shared OpenRouter client, but knows nothing about
Django, Celery, or HTTP routing.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Final

from pydantic import ValidationError

from classification.application.prompts import (
    build_messages,
    build_validation_messages,
)
from classification.domain.confidence import (
    CONFIDENCE_HIGH_THRESHOLD,
    CONFIDENCE_MEDIUM_THRESHOLD,
)
from classification.domain.contract_type import ContractType
from classification.domain.dtos import ClassificationResult
from shared.llm.openrouter import (
    ChatCompletionResult,
    OpenRouterClient,
    OpenRouterError,
)

logger = logging.getLogger(__name__)


DEFAULT_CLASSIFICATION_MODEL: Final[str] = "anthropic/claude-sonnet-4"
"""Aligned with ``LLM_CLASSIFICATION_MODEL`` default in PRD F2 §6.3."""

DEFAULT_TEMPERATURE: Final[float] = 0.1
"""Deterministic-but-not-frozen sampling per PRD F2 §6.3."""


_JSON_FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*```(?:json)?\s*|\s*```\s*$",
    flags=re.IGNORECASE,
)


def _is_high_confidence(score: float) -> bool:
    """Return True when the primary call should be accepted as-is.

    BVA: strict `>` so 0.85 falls into the retry band (PRD F2 §US-01).
    Constant comes from `confidence.py` to keep a single source of truth.
    """
    return score > CONFIDENCE_HIGH_THRESHOLD


def _is_medium_confidence(score: float) -> bool:
    """Return True when the §8.3 validator should run.

    BVA: inclusive lower (`>=`) so 0.65 triggers validation, and inclusive
    upper (`<=`) so 0.85 routes here (PRD F2 §US-01). The strict / inclusive
    asymmetry mirrors the PRD verbatim.
    """
    return CONFIDENCE_MEDIUM_THRESHOLD <= score <= CONFIDENCE_HIGH_THRESHOLD


class ClassificationError(RuntimeError):
    """Raised when the classifier cannot produce a valid result.

    Carries an optional ``code`` so callers (CS-112+) can map this onto
    the canonical F2 error codes (``LLM_PARSE_FAILED``,
    ``LLM_TRANSIENT_FAILURE``, etc.) without parsing the message.
    """

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class ContractClassifier:
    """High-level service that turns OCR'd contract text into a label.

    The client is injected so tests (deferred to CS-115) and orchestrators
    can plug in mocks or share a single HTTPX connection pool.
    """

    def __init__(
        self,
        *,
        client: OpenRouterClient | None = None,
        model: str = DEFAULT_CLASSIFICATION_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        self._client = client or OpenRouterClient()
        self._owns_client = client is None
        self._model = model
        self._temperature = temperature

    def __enter__(self) -> ContractClassifier:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def classify(self, extracted_text: str) -> ClassificationResult:
        """Run the PRD F2 §US-01 confidence-band classification protocol.

        Returns a :class:`ClassificationResult` with ``classification_attempts``
        set to 1 (primary accepted or low-confidence reject) or 2 (validator
        fired). ``NOT_CLASSIFIABLE`` is a legitimate value here — only true
        LLM / schema failures raise :class:`ClassificationError`.

        :raises ClassificationError: if the LLM call fails after the
            shared client's retry budget, or if the response cannot be
            parsed into a :class:`ClassificationResult`.
        """
        if not extracted_text or not extracted_text.strip():
            raise ClassificationError(
                "extracted_text is empty",
                code="EMPTY_INPUT",
            )

        primary = self._run_primary(extracted_text)

        if _is_high_confidence(primary.confidence):
            return primary  # attempts=1 default

        if primary.confidence < CONFIDENCE_MEDIUM_THRESHOLD:
            logger.info(
                "classification.low_confidence_rejected",
                extra={
                    "primary_type": primary.contract_type.value,
                    "primary_confidence": primary.confidence,
                },
            )
            return primary.model_copy(
                update={
                    "contract_type": ContractType.NOT_CLASSIFIABLE,
                    "classification_attempts": 1,
                },
            )

        # 0.65 ≤ confidence ≤ 0.85 → validation pass.
        validator = self._run_validator(extracted_text, prior=primary)
        return self._apply_validator(primary, validator)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _run_primary(self, extracted_text: str) -> ClassificationResult:
        return self._invoke(
            build_messages(extracted_text),
            stage="primary",
        )

    def _run_validator(
        self,
        extracted_text: str,
        *,
        prior: ClassificationResult,
    ) -> ClassificationResult:
        return self._invoke(
            build_validation_messages(
                extracted_text,
                prior_type=prior.contract_type.value,
                prior_reasoning=prior.reasoning,
            ),
            stage="validator",
        )

    def _apply_validator(
        self,
        primary: ClassificationResult,
        validator: ClassificationResult,
    ) -> ClassificationResult:
        """Reconcile primary + validator outputs per PRD F2 §US-01."""
        agrees = validator.contract_type == primary.contract_type
        validator_confident = validator.confidence > CONFIDENCE_MEDIUM_THRESHOLD

        if agrees and validator_confident:
            logger.info(
                "classification.validator_confirmed",
                extra={
                    "type": primary.contract_type.value,
                    "primary_confidence": primary.confidence,
                    "validator_confidence": validator.confidence,
                },
            )
            return validator.model_copy(update={"classification_attempts": 2})

        logger.info(
            "classification.validator_rejected",
            extra={
                "primary_type": primary.contract_type.value,
                "primary_confidence": primary.confidence,
                "validator_type": validator.contract_type.value,
                "validator_confidence": validator.confidence,
                "agrees": agrees,
                "validator_confident": validator_confident,
            },
        )
        return primary.model_copy(
            update={
                "contract_type": ContractType.NOT_CLASSIFIABLE,
                "classification_attempts": 2,
            },
        )

    def _invoke(
        self,
        messages: list[dict[str, str]],
        *,
        stage: str,
    ) -> ClassificationResult:
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
                "classification.openrouter_error",
                extra={
                    "model": self._model,
                    "stage": stage,
                    "status_code": exc.status_code,
                },
            )
            raise ClassificationError(
                f"OpenRouter call failed during {stage}: {exc}",
                code="LLM_TRANSIENT_FAILURE",
            ) from exc

        return self._parse(completion)

    def _parse(self, completion: ChatCompletionResult) -> ClassificationResult:
        raw = (completion.content or "").strip()
        cleaned = _JSON_FENCE_RE.sub("", raw).strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(
                "classification.parse_failed",
                extra={"model": self._model, "error": str(exc)},
            )
            raise ClassificationError(
                "LLM returned non-JSON content",
                code="LLM_PARSE_FAILED",
            ) from exc

        try:
            return ClassificationResult.model_validate(payload)
        except ValidationError as exc:
            logger.warning(
                "classification.schema_violation",
                extra={"model": self._model, "error": str(exc)},
            )
            raise ClassificationError(
                "LLM JSON did not match ClassificationResult schema",
                code="LLM_PARSE_FAILED",
            ) from exc
