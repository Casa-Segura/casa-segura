"""Primary contract classification service (CS-110).

Orchestrates one OpenRouter chat-completion call against the prompts
defined in :mod:`classification.application.prompts` and returns a
validated :class:`~classification.domain.dtos.ClassificationResult`.

Scope (per CS-110):

* Single primary call (the §8.3 validation pass, confidence banding,
  leasing detection, and persistence live in sibling tickets).
* Deterministic generation (``temperature=0.1`` matching the PRD F2 §6.3
  default ``LLM_TEMPERATURE``).
* Defensive parsing: strip code fences and surface a typed error rather
  than a raw stack trace if the model returns malformed JSON.

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

from classification.application.prompts import build_messages
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
        """Run a single classification pass over ``extracted_text``.

        :raises ClassificationError: if the LLM call fails after the
            shared client's retry budget, or if the response cannot be
            parsed into a :class:`ClassificationResult`.
        """
        if not extracted_text or not extracted_text.strip():
            raise ClassificationError(
                "extracted_text is empty",
                code="EMPTY_INPUT",
            )

        messages = build_messages(extracted_text)

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
                    "status_code": exc.status_code,
                },
            )
            raise ClassificationError(
                f"OpenRouter call failed: {exc}",
                code="LLM_TRANSIENT_FAILURE",
            ) from exc

        return self._parse(completion)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
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
