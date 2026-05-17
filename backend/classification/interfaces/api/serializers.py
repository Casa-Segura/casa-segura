"""DRF serializers for the internal `/api/v1/internal/classify` endpoint."""

from __future__ import annotations

from rest_framework import serializers


class InternalClassifyRequestSerializer(serializers.Serializer):
    """Request body for the F2 orchestrator QA endpoint.

    Both fields are required; the orchestrator persists keyed by
    ``submission_hash`` (idempotent retries) and runs the LLM chain over
    the provided ``extracted_text``. The endpoint is intentionally
    decoupled from the public ingestion pipeline so QA can replay
    contracts without re-uploading bytes.
    """

    submission_hash = serializers.CharField(
        max_length=64,
        help_text="SHA-256 hex string identifying the submission (idempotency key).",
    )
    extracted_text = serializers.CharField(
        help_text="OCR'd contract text. Sent in-memory, never persisted by the endpoint.",
    )


class _ClassificationEnvelopeSerializer(serializers.Serializer):
    contract_type = serializers.CharField()
    confidence = serializers.FloatField()
    classification_attempts = serializers.IntegerField()
    reasoning = serializers.CharField(allow_null=True)
    indicators_found = serializers.ListField(child=serializers.CharField())
    elements_detected = serializers.DictField()


class _LeasingEnvelopeSerializer(serializers.Serializer):
    original_type = serializers.CharField()
    recommended_type = serializers.CharField()
    should_reclassify = serializers.BooleanField()
    severity = serializers.CharField()
    count = serializers.IntegerField()
    confidence = serializers.FloatField()
    reasoning = serializers.CharField(allow_null=True)
    indicators = serializers.DictField()


class _AggregatedEnvelopeSerializer(serializers.Serializer):
    slots = serializers.DictField()
    unverifiable_fields = serializers.ListField(child=serializers.CharField())
    ambiguous_count = serializers.IntegerField()
    warning_precursors = serializers.ListField(child=serializers.CharField())


class InternalClassifyResponseSerializer(serializers.Serializer):
    """Serialized :class:`F2OrchestratorResult` for QA consumption."""

    contract_analysis_id = serializers.UUIDField()
    public_short_id = serializers.CharField()
    effective_contract_type = serializers.CharField()
    was_created = serializers.BooleanField()
    classification = _ClassificationEnvelopeSerializer()
    leasing = _LeasingEnvelopeSerializer()
    aggregated = _AggregatedEnvelopeSerializer()
