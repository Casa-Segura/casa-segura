"""Per-contract-type economic field extraction service (CS-113).

Given the OCR'd contract text and the :class:`ContractType` produced by
CS-110, ``EconomicFieldExtractor`` runs a single OpenRouter call against
the per-type prompt from
:mod:`classification.application.economic_prompts` and returns a
populated :class:`ContractExtraction` whose:

* ``extracted_fields`` is a validated :class:`ExtractedFields` with the
  fields the LLM successfully extracted.
* ``field_confidences`` carries a :class:`ConfidenceBand` for every
  extracted field, built from the LLM's per-field ``confidence`` and
  optional ``rationale``.
* ``unverifiable_fields`` is the PRD_F2 BR-07 list of required-but-
  missing fields for this contract type, computed via CS-114's
  :func:`classify_unverifiable`.

Failure surface (CRITICAL):
    * Transport / 5xx exhaustion → :class:`EconomicExtractionError`
      (``LLM_TRANSIENT_FAILURE``).
    * JSON parse failure → :class:`EconomicExtractionError`
      (``LLM_PARSE_FAILED``).
    * Per-field validation failure (e.g. negative price, out-of-range
      percentage, malformed enum) → the field is **demoted to
      ``unverifiable``** rather than raised. This satisfies the CS-113
      AC: "if the LLM returns a field value that fails the pydantic
      field validator on ``ExtractedFields``, surface that field as
      ``unverifiable`` rather than crashing."

DDD note:
    This is the application layer. It depends on the domain (DTOs,
    enums, validation) and on the shared OpenRouter infrastructure
    client, but knows nothing about Django, Celery, or HTTP routing.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Final

from pydantic import ValidationError

from classification.application.economic_prompts import build_messages
from classification.application.errors import EconomicExtractionError
from classification.application.extraction_policy import (
    REQUIRED_FIELDS_BY_TYPE,
    classify_unverifiable,
)
from classification.application.value_coercion import (
    coerce_currency,
    coerce_float,
    coerce_int,
    coerce_interest_base,
    coerce_payment_periodicity,
    coerce_pct_as_decimal,
)
from classification.domain.confidence import ConfidenceBand
from classification.domain.contract_extraction import ContractExtraction
from classification.domain.contract_type import ContractType
from classification.domain.extracted_fields import ExtractedFields
from shared.llm.openrouter import (
    ChatCompletionResult,
    OpenRouterClient,
    OpenRouterError,
)

logger = logging.getLogger(__name__)


DEFAULT_EXTRACTION_MODEL: Final[str] = "anthropic/claude-sonnet-4"
"""Same model family as CS-110; PRD F2 §6.3 ``LLM_CLASSIFICATION_MODEL``."""

DEFAULT_TEMPERATURE: Final[float] = 0.1
"""Deterministic-but-not-frozen sampling per PRD F2 §6.3."""


_JSON_FENCE_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*```(?:json)?\s*|\s*```\s*$",
    flags=re.IGNORECASE,
)


# Coercion strategy per `ExtractedFields` attribute name. Keys are the
# attribute names; values are callables `(raw) -> coerced_or_None`. Kept
# at module scope so the dispatch table is easy to audit alongside the
# field declarations in `extracted_fields.py`.
_FIELD_COERCERS: Final[dict[str, Any]] = {
    # Money in USD.
    "purchase_price_usd": coerce_float,
    "down_payment_usd": coerce_float,
    "financed_amount_usd": coerce_float,
    "monthly_payment_usd": coerce_float,
    "monthly_rent_usd": coerce_float,
    "deposit_usd": coerce_float,
    "purchase_option_price_usd": coerce_float,
    # Decimal fractions in [0, 1] (or close to it; F5 final-validates).
    "down_payment_pct": coerce_pct_as_decimal,
    "interest_rate_pct": coerce_pct_as_decimal,
    "monthly_rate_pct": coerce_pct_as_decimal,
    # Integer counts.
    "term_months": coerce_int,
    "installment_count": coerce_int,
    # Closed-set strings.
    "currency": coerce_currency,
    "payment_periodicity": coerce_payment_periodicity,
    "interest_calculation_base": coerce_interest_base,
    # Free-form strings — pass-through with whitespace trim.
    "project_name_raw": lambda v: v.strip() if isinstance(v, str) and v.strip() else None,
    "property_address": lambda v: v.strip() if isinstance(v, str) and v.strip() else None,
    "seller_name": lambda v: v.strip() if isinstance(v, str) and v.strip() else None,
    "buyer_name": lambda v: v.strip() if isinstance(v, str) and v.strip() else None,
}


class EconomicFieldExtractor:
    """High-level service that turns contract text + type into a typed extraction.

    The OpenRouter client is injected so orchestrators can share one
    HTTPX pool across CS-110 / CS-111 / CS-112 / CS-113 and so future
    tests (CS-115) can wire a ``respx`` transport without touching the
    network.
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

    def __enter__(self) -> EconomicFieldExtractor:
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
        contract_type: ContractType,
    ) -> ContractExtraction:
        """Run one extraction pass and return a :class:`ContractExtraction`.

        Short-circuits on ``NOT_CLASSIFIABLE``: returns an empty
        extraction (no LLM call) since the submission will be rejected
        by F2's orchestrator anyway (PRD_F2 US-06).
        """
        if contract_type is ContractType.NOT_CLASSIFIABLE:
            return ContractExtraction(
                contract_type=contract_type,
                extracted_fields=ExtractedFields(),
                field_confidences={},
                unverifiable_fields=[],
            )

        if not extracted_text or not extracted_text.strip():
            raise EconomicExtractionError(
                "extracted_text is empty",
                code="EMPTY_INPUT",
            )

        messages = build_messages(extracted_text, contract_type)

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
                "economic_extraction.openrouter_error",
                extra={
                    "model": self._model,
                    "contract_type": contract_type.value,
                    "status_code": exc.status_code,
                },
            )
            raise EconomicExtractionError(
                f"OpenRouter call failed: {exc}",
                code="LLM_TRANSIENT_FAILURE",
            ) from exc

        payload = self._parse_payload(completion, contract_type)
        return self._build_extraction(payload, contract_type)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _parse_payload(
        self,
        completion: ChatCompletionResult,
        contract_type: ContractType,
    ) -> dict[str, Any]:
        """Strip code fences, parse JSON, and verify the top-level shape."""
        raw = (completion.content or "").strip()
        cleaned = _JSON_FENCE_RE.sub("", raw).strip()
        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.warning(
                "economic_extraction.parse_failed",
                extra={
                    "model": self._model,
                    "contract_type": contract_type.value,
                    "error": str(exc),
                },
            )
            raise EconomicExtractionError(
                "LLM returned non-JSON content",
                code="LLM_PARSE_FAILED",
            ) from exc

        if not isinstance(payload, dict):
            logger.warning(
                "economic_extraction.shape_violation",
                extra={
                    "model": self._model,
                    "contract_type": contract_type.value,
                    "received_type": type(payload).__name__,
                },
            )
            raise EconomicExtractionError(
                "LLM response was valid JSON but not an object",
                code="LLM_PARSE_FAILED",
            )
        return payload

    def _build_extraction(
        self,
        payload: dict[str, Any],
        contract_type: ContractType,
    ) -> ContractExtraction:
        """Coerce LLM values, validate per-field, build the wrapper.

        Per CS-113 AC, a field that the LLM returned but that fails
        :class:`ExtractedFields` validation (e.g. negative price) is
        demoted to ``unverifiable`` instead of crashing the call. We
        achieve this by (a) coercing each value with the dispatch in
        :data:`_FIELD_COERCERS`, (b) building the model one field at a
        time so we can catch validation per-field, and (c) merging the
        BR-07 ``unverifiable_fields`` list at the end.
        """
        accepted_values: dict[str, Any] = {}
        accepted_confidences: dict[str, ConfidenceBand] = {}
        demoted_fields: set[str] = set()
        ambiguous_fields: set[str] = set()
        known_attrs = set(ExtractedFields.model_fields.keys())

        for field_name, raw_entry in payload.items():
            if field_name not in known_attrs:
                # Silently drop unknown keys: the LLM occasionally
                # invents fields, and `ExtractedFields` has
                # `extra="forbid"`. Logging at debug because the prompt
                # is already strict about the menu.
                logger.debug(
                    "economic_extraction.unknown_field",
                    extra={"field": field_name},
                )
                continue
            if not isinstance(raw_entry, dict):
                # Field returned as a bare value instead of `{value, ...}`.
                # We treat the whole entry as a `value` with no confidence.
                raw_value = raw_entry
                raw_confidence: Any = None
                rationale = None
                extraction_status: str | None = None
            else:
                raw_value = raw_entry.get("value")
                raw_confidence = raw_entry.get("confidence")
                rationale = raw_entry.get("rationale")
                if isinstance(rationale, str):
                    rationale = rationale[:500]
                else:
                    rationale = None
                status_raw = raw_entry.get("extraction_status")
                extraction_status = (
                    status_raw.strip().lower() if isinstance(status_raw, str) and status_raw.strip() else None
                )

            # Ambiguity short-circuit (CS-113 + CS-116). PRD_F2 US-04: when
            # the contract carries conflicting figures for the same field,
            # the LLM signals `extraction_status="ambiguous"`. We suppress
            # the numeric value (BR-09 honesty: no silent guess) and route
            # the field through `ambiguous_fields` so CS-116's aggregator
            # tags the slot as `ExtractionStatus.AMBIGUOUS` rather than
            # falling back to `not_present` or substituting zero.
            if extraction_status == "ambiguous":
                logger.info(
                    "economic_extraction.field_ambiguous",
                    extra={"field": field_name, "contract_type": contract_type.value},
                )
                ambiguous_fields.add(field_name)
                continue

            coercer = _FIELD_COERCERS.get(field_name)
            coerced = coercer(raw_value) if coercer is not None else raw_value
            if coerced is None:
                # Either the LLM returned null / blank, or coercion failed.
                # Either way, the field is missing from this extraction
                # — `classify_unverifiable` will surface it if required.
                continue

            # Per-field validation: construct an `ExtractedFields` with
            # just this attribute set so the field-level validators fire
            # in isolation. If validation fails, demote the field.
            try:
                ExtractedFields(**{field_name: coerced})
            except ValidationError as exc:
                logger.info(
                    "economic_extraction.field_invalid",
                    extra={
                        "field": field_name,
                        "contract_type": contract_type.value,
                        "errors": exc.error_count(),
                    },
                )
                demoted_fields.add(field_name)
                continue

            accepted_values[field_name] = coerced
            band = _build_confidence_band(raw_confidence, rationale)
            if band is not None:
                accepted_confidences[field_name] = band

        try:
            extracted = ExtractedFields(**accepted_values)
        except ValidationError as exc:
            # All values were individually validated; a cross-field
            # validator (none exist today, but future ones may) failed.
            # Treat this as a parse failure rather than silently shipping
            # an inconsistent extraction.
            logger.warning(
                "economic_extraction.model_invalid",
                extra={
                    "model": self._model,
                    "contract_type": contract_type.value,
                    "errors": exc.error_count(),
                },
            )
            raise EconomicExtractionError(
                "extracted values failed ExtractedFields model validation",
                code="LLM_PARSE_FAILED",
            ) from exc

        unverifiable = set(classify_unverifiable(extracted, contract_type))
        # Demoted fields are also `unverifiable` if the type requires them.
        # We additionally surface demoted *non-required* fields so callers
        # can see the LLM tried and we rejected — useful for QA without
        # changing the rubric path.
        required_for_type = REQUIRED_FIELDS_BY_TYPE.get(contract_type, set())
        unverifiable |= demoted_fields & required_for_type

        return ContractExtraction(
            contract_type=contract_type,
            extracted_fields=extracted,
            field_confidences=accepted_confidences,
            unverifiable_fields=sorted(unverifiable),
            ambiguous_fields=sorted(ambiguous_fields),
        )


def _build_confidence_band(
    raw_confidence: Any,
    rationale: str | None,
) -> ConfidenceBand | None:
    """Build a :class:`ConfidenceBand` from raw LLM confidence + rationale.

    Returns ``None`` when the LLM omitted the score or returned a value
    outside ``[0, 1]`` — the field is still kept (value already coerced),
    but no band is recorded, mirroring CS-114's invariant that an absent
    band means "classifier did not provide a confidence".
    """
    if raw_confidence is None:
        return None
    try:
        score = float(raw_confidence)
    except (TypeError, ValueError):
        return None
    if not (0.0 <= score <= 1.0):
        return None
    return ConfidenceBand.from_score(score, rationale=rationale)


__all__ = [
    "DEFAULT_EXTRACTION_MODEL",
    "DEFAULT_TEMPERATURE",
    "EconomicFieldExtractor",
]
