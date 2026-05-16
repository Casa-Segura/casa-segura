"""Project-name extraction service (CS-112).

Pipeline:
    1. Call OpenRouter with the §8.2-style prompts in
       :mod:`classification.application.project_name_prompts`
       (``temperature=0.1``, ``response_format=json_object``).
    2. Parse the response into ``{"project_name_raw": str | null,
       "confidence": float}``.
    3. Run the verbatim text through
       :func:`platform_core.domain.project_name.normalize_project_name`.
    4. If the normalized result is empty (LLM returned nothing OR the
       normalized form was shorter than the 3-character floor), substitute
       the deterministic placeholder ``unknown_<short_hash>``.

Placeholder hash derivation
---------------------------
The placeholder format is ``unknown_<short_hash>`` where ``<short_hash>``
is the first **8 hex characters of the SHA-256 of the raw extracted
contract text**. Rationale:

* Stable: the same submission always yields the same placeholder, so
  retries within a single submission lifecycle do NOT create duplicate
  Project rows. (Two *different* submissions with the same OCR'd bytes
  also collide, which is acceptable — they are the same contract.)
* Distinct across submissions: any byte-level change in the OCR output
  produces a different hash, satisfying PRD_F8 BR-07 ("placeholder
  projects are NOT reused across submissions").
* SHA-256 (not the submission hash from `ContractSubmission`) keeps this
  service decoupled from the persistence layer — the extractor does not
  need to know whether a `submission_hash` already exists on the row.
  When CS-112 is wired into the orchestrator, callers MAY override the
  derivation by passing ``placeholder_seed=`` (e.g. the canonical
  `submission_hash`) so the placeholder echoes the row's identity.
* 8 hex chars = 32 bits = enough entropy to avoid placeholder collisions
  in the foreseeable submission volume (~4B distinct placeholders before
  birthday-paradox risk).

The pattern matches the regex enforced by
:func:`platform_core.domain.project_name.is_placeholder_normalized_name`
(``^unknown_[0-9a-f]+$``).

DDD layering
------------
This module lives in ``classification.application``. It depends on:

* ``classification.domain.project_name_extraction`` (DTO)
* ``classification.application.project_name_prompts`` (prompt builder)
* ``platform_core.domain.project_name`` (pure normalization helpers,
  domain-layer — no Django coupling, see ADR-0002 / CS-031)
* ``shared.llm.openrouter`` (LLM client)

It does NOT touch the ORM. Linkage is the responsibility of
``ProjectLinker`` in :mod:`classification.application.project_linker`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Final

from pydantic import ValidationError

from classification.application.project_name_prompts import build_messages
from classification.domain.project_name_extraction import ProjectNameExtraction
from platform_core.domain.project_name import normalize_project_name
from shared.llm.openrouter import (
    ChatCompletionResult,
    OpenRouterClient,
    OpenRouterError,
)

logger = logging.getLogger(__name__)


DEFAULT_EXTRACTION_MODEL: Final[str] = "anthropic/claude-sonnet-4"
"""Aligned with ``LLM_CLASSIFICATION_MODEL`` default in PRD F2 §6.3."""

DEFAULT_TEMPERATURE: Final[float] = 0.1
"""Deterministic-but-not-frozen sampling per PRD F2 §6.3."""

PLACEHOLDER_PREFIX: Final[str] = "unknown_"
PLACEHOLDER_HASH_LEN: Final[int] = 8


_JSON_FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*```(?:json)?\s*|\s*```\s*$",
    flags=re.IGNORECASE,
)


class ProjectNameExtractionError(RuntimeError):
    """Raised when the extractor cannot produce a valid result.

    Carries an optional ``code`` so orchestrators can map this onto the
    canonical F2 error codes (``LLM_PARSE_FAILED``, ``LLM_TRANSIENT_FAILURE``,
    ``EMPTY_INPUT``) without parsing the message.
    """

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


def build_placeholder(extracted_text: str) -> str:
    """Return the deterministic ``unknown_<short_hash>`` placeholder for `extracted_text`.

    See module docstring for the derivation rationale (SHA-256 of the
    extracted text, first 8 hex chars).
    """
    digest = hashlib.sha256(extracted_text.encode("utf-8")).hexdigest()
    return f"{PLACEHOLDER_PREFIX}{digest[:PLACEHOLDER_HASH_LEN]}"


class ProjectNameExtractor:
    """Application service that turns OCR'd contract text into a `ProjectNameExtraction`.

    The OpenRouter client is injected so tests and orchestrators can plug
    in mocks or share a single connection pool, matching the pattern in
    :class:`classification.application.classifier.ContractClassifier`.
    """

    def __init__(
        self,
        *,
        client: OpenRouterClient | None = None,
        model: str = DEFAULT_EXTRACTION_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> None:
        self._client = client or OpenRouterClient()
        self._owns_client = client is None
        self._model = model
        self._temperature = temperature

    def __enter__(self) -> ProjectNameExtractor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def extract(
        self,
        extracted_text: str,
        *,
        placeholder_seed: str | None = None,
    ) -> ProjectNameExtraction:
        """Run a single project-name extraction pass over ``extracted_text``.

        Args:
            extracted_text: full OCR'd contract text (in memory; never
                persisted by this service).
            placeholder_seed: optional override for the placeholder hash
                input. When ``None``, the SHA-256 of ``extracted_text`` is
                used (see module docstring). Pass the canonical
                ``submission_hash`` here to keep placeholders aligned
                with the persisted row identity.

        Returns:
            A populated :class:`ProjectNameExtraction`. The ``normalized``
            field is always non-empty: either the normalized form of the
            LLM's raw text, or an ``unknown_<short_hash>`` placeholder.

        Raises:
            ProjectNameExtractionError: if the input is empty, the LLM
                call fails, or the response cannot be parsed.
        """
        if not extracted_text or not extracted_text.strip():
            raise ProjectNameExtractionError(
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
                "project_name_extraction.openrouter_error",
                extra={
                    "model": self._model,
                    "status_code": exc.status_code,
                },
            )
            raise ProjectNameExtractionError(
                f"OpenRouter call failed: {exc}",
                code="LLM_TRANSIENT_FAILURE",
            ) from exc

        raw, confidence = self._parse(completion)
        normalized = normalize_project_name(raw)

        if not normalized:
            seed = placeholder_seed if placeholder_seed is not None else extracted_text
            normalized = build_placeholder(seed)

        # `is_placeholder` is derived inside the DTO from `normalized`; we
        # pass `False` and let the validator overwrite when the regex hits.
        return ProjectNameExtraction(
            raw=raw,
            normalized=normalized,
            is_placeholder=False,
            confidence=confidence,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _parse(self, completion: ChatCompletionResult) -> tuple[str | None, float]:
        """Return ``(project_name_raw, confidence)`` from a chat completion.

        Strips JSON code fences defensively (some models return fenced
        content even when ``response_format=json_object`` is requested).
        """
        raw_content = (completion.content or "").strip()
        cleaned = _JSON_FENCE_RE.sub("", raw_content).strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(
                "project_name_extraction.parse_failed",
                extra={"model": self._model, "error": str(exc)},
            )
            raise ProjectNameExtractionError(
                "LLM returned non-JSON content",
                code="LLM_PARSE_FAILED",
            ) from exc

        if not isinstance(payload, dict):
            raise ProjectNameExtractionError(
                "LLM JSON root is not an object",
                code="LLM_PARSE_FAILED",
            )

        raw_value = payload.get("project_name_raw")
        if raw_value is not None and not isinstance(raw_value, str):
            raise ProjectNameExtractionError(
                "project_name_raw must be string or null",
                code="LLM_PARSE_FAILED",
            )
        # Normalise empty strings to `None` so the placeholder path triggers.
        if isinstance(raw_value, str) and not raw_value.strip():
            raw_value = None

        confidence_value = payload.get("confidence")
        if not isinstance(confidence_value, (int, float)):
            raise ProjectNameExtractionError(
                "confidence must be a number",
                code="LLM_PARSE_FAILED",
            )

        try:
            # Round-trip through the DTO's validator catches out-of-range
            # values via the same path the final DTO will use.
            _ = ProjectNameExtraction(
                raw=raw_value,
                normalized="placeholder_for_validation_only",
                is_placeholder=False,
                confidence=float(confidence_value),
            )
        except ValidationError as exc:
            logger.warning(
                "project_name_extraction.schema_violation",
                extra={"model": self._model, "error": str(exc)},
            )
            raise ProjectNameExtractionError(
                "LLM JSON did not match ProjectNameExtraction schema",
                code="LLM_PARSE_FAILED",
            ) from exc

        return raw_value, float(confidence_value)


__all__ = [
    "DEFAULT_EXTRACTION_MODEL",
    "DEFAULT_TEMPERATURE",
    "PLACEHOLDER_HASH_LEN",
    "PLACEHOLDER_PREFIX",
    "ProjectNameExtractionError",
    "ProjectNameExtractor",
    "build_placeholder",
]
