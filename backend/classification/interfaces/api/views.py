"""Internal QA endpoint for the F2 orchestrator (CS-115 dependency).

``POST /api/v1/internal/classify`` runs the chain
:func:`F2Orchestrator.run` against caller-supplied text and returns a
serialized envelope. Gated by :class:`IsInternal` (shared-secret header
``X-Internal-Token``). Production classification runs from inside the
ingestion worker via the same orchestrator; this endpoint exists only
so QA / eval harnesses (CS-115) can replay corpus contracts without
re-uploading bytes.
"""

from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from classification.application.orchestrator import (
    F2Orchestrator,
    F2OrchestratorError,
    F2OrchestratorResult,
)
from classification.interfaces.api.serializers import (
    InternalClassifyRequestSerializer,
    InternalClassifyResponseSerializer,
)
from shared.security.internal_auth import IsInternal

logger = logging.getLogger(__name__)


def _envelope_from_result(result: F2OrchestratorResult) -> dict:
    """Project the dataclass result into the response shape."""
    classification = result.classification
    leasing = result.leasing
    aggregated = result.aggregated

    return {
        "contract_analysis_id": result.contract_analysis_id,
        "public_short_id": result.public_short_id,
        "effective_contract_type": result.effective_contract_type.value,
        "was_created": result.was_created,
        "classification": {
            "contract_type": classification.contract_type.value,
            "confidence": classification.confidence,
            "classification_attempts": classification.classification_attempts,
            "reasoning": classification.reasoning,
            "indicators_found": list(classification.indicators_found.items),
            "elements_detected": classification.elements_detected.model_dump(),
        },
        "leasing": {
            "original_type": leasing.original_type.value,
            "recommended_type": leasing.recommended_type.value,
            "should_reclassify": leasing.should_reclassify,
            "severity": leasing.severity.value,
            "count": leasing.indicators.total_indicators_found,
            "confidence": leasing.confidence,
            "reasoning": leasing.reasoning,
            "indicators": leasing.indicators.model_dump(),
        },
        "aggregated": {
            "slots": {
                name: {
                    "status": slot.status.value,
                    "value": slot.value,
                    "confidence": slot.confidence,
                }
                for name, slot in aggregated.slots.items()
            },
            "unverifiable_fields": list(aggregated.unverifiable_fields),
            "ambiguous_count": aggregated.ambiguous_count,
            "warning_precursors": list(aggregated.warning_precursors),
        },
    }


class InternalClassifyView(APIView):
    """`POST /api/v1/internal/classify` — run the F2 orchestrator on raw text."""

    permission_classes = (IsInternal,)

    def post(self, request) -> Response:
        request_serializer = InternalClassifyRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        payload = request_serializer.validated_data

        try:
            with F2Orchestrator() as orchestrator:
                result = orchestrator.run(
                    submission_hash=payload["submission_hash"],
                    extracted_text=payload["extracted_text"],
                )
        except F2OrchestratorError as exc:
            logger.warning(
                "internal_classify.orchestrator_error",
                extra={"code": exc.code},
            )
            http_status = (
                status.HTTP_400_BAD_REQUEST
                if exc.code in {"EMPTY_INPUT", "FAILED_CLASSIFICATION"}
                else status.HTTP_502_BAD_GATEWAY
            )
            return Response(
                {"error": {"code": exc.code or "ORCHESTRATOR_ERROR", "message": str(exc)}},
                status=http_status,
            )

        response_body = _envelope_from_result(result)
        return Response(
            InternalClassifyResponseSerializer(response_body).data,
            status=status.HTTP_200_OK,
        )
