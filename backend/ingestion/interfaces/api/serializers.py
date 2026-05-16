"""DRF serializers for the ingestion API."""

from __future__ import annotations

from rest_framework import serializers

from ingestion.domain.enums import DisclaimerAcceptanceMethod, SubmissionSource
from ingestion.infrastructure.django.models import ContractSubmission


class SubmissionUploadSerializer(serializers.Serializer):
    """Accepts a single multipart upload + disclaimer metadata."""

    file = serializers.FileField()
    disclaimer_accepted_at = serializers.DateTimeField(required=False, allow_null=True)
    disclaimer_method = serializers.ChoiceField(
        choices=DisclaimerAcceptanceMethod.choices,
        default=DisclaimerAcceptanceMethod.CHECKBOX.value,
    )
    source = serializers.ChoiceField(
        choices=SubmissionSource.choices,
        default=SubmissionSource.WEB.value,
    )


class SubmissionResponseSerializer(serializers.ModelSerializer):
    """Stable response shape for upload/status calls."""

    class Meta:
        model = ContractSubmission
        fields = (
            "id",
            "submission_hash",
            "file_format",
            "file_size_bytes",
            "page_count",
            "source",
            "processing_status",
            "extraction_strategy_attempted",
            "extraction_strategy_successful",
            "extracted_text_token_count",
            "extracted_text_language",
            "error_code",
            "error_reason",
            "received_at",
            "expires_at",
        )
        read_only_fields = fields
