"""DRF serializers for the ingestion API."""

from __future__ import annotations

from rest_framework import serializers

from ingestion.domain.enums import DisclaimerAcceptanceMethod, SubmissionSource
from ingestion.infrastructure.django.models import ContractSubmission


class SubmissionUploadSerializer(serializers.Serializer):
    """Accepts a multipart upload (legacy ``file`` or PRD §US-01 ``files[]``)
    plus disclaimer metadata."""

    file = serializers.FileField(required=False)
    disclaimer_method = serializers.ChoiceField(
        choices=DisclaimerAcceptanceMethod.choices,
        default=DisclaimerAcceptanceMethod.CHECKBOX.value,
    )
    source = serializers.ChoiceField(
        choices=SubmissionSource.choices,
        default=SubmissionSource.WEB.value,
    )

    def validate(self, attrs):
        # The view passes `file_count` so the serializer can require at
        # least one upload without forcing a specific field name.
        file_count = (self.context or {}).get("file_count", 0)
        if file_count == 0 and "file" not in attrs:
            raise serializers.ValidationError(
                {"file": "at least one file must be supplied (file= or files=)"}
            )
        return attrs


class SubmissionResponseSerializer(serializers.ModelSerializer):
    """Stable response shape for upload/status calls."""

    class Meta:
        model = ContractSubmission
        fields = (
            "id",
            "submission_hash",
            "file_format",
            "file_count",
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
