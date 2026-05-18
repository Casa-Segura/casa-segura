"""DRF serializers for the ingestion API."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import EmailValidator
from rest_framework import serializers

from ingestion.domain.enums import DisclaimerAcceptanceMethod, SubmissionSource
from ingestion.infrastructure.django.models import ContractSubmission

_E164_RE = re.compile(r"^\+[1-9]\d{1,14}$")


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
    delivery_channel = serializers.ChoiceField(
        choices=("sms_summary", "email_pdf", "web_link"),
        default="web_link",
        required=False,
    )
    delivery_target = serializers.CharField(required=False, allow_blank=True, max_length=320)

    def validate(self, attrs):
        # The view passes `file_count` so the serializer can require at
        # least one upload without forcing a specific field name.
        file_count = (self.context or {}).get("file_count", 0)
        if file_count == 0 and "file" not in attrs:
            raise serializers.ValidationError({"file": "at least one file must be supplied (file= or files=)"})

        channel = (attrs.get("delivery_channel") or "web_link").strip().lower()
        raw_target = attrs.get("delivery_target")
        target = raw_target.strip() if isinstance(raw_target, str) else ""
        attrs["delivery_channel"] = channel

        if channel == "web_link":
            attrs["delivery_target"] = None
            return attrs

        if channel in ("sms_summary", "email_pdf") and not target:
            raise serializers.ValidationError(
                {"delivery_target": "Este canal requiere un destino (teléfono E.164 o correo)."}
            )

        if channel == "sms_summary":
            if not _E164_RE.fullmatch(target):
                raise serializers.ValidationError(
                    {"delivery_target": "Usá formato internacional E.164, por ejemplo +503XXXXXXXX."}
                )
            attrs["delivery_target"] = target
            return attrs

        # email_pdf
        validator = EmailValidator()
        try:
            validator(target)
        except DjangoValidationError:
            raise serializers.ValidationError({"delivery_target": "Correo electrónico inválido."}) from None
        attrs["delivery_target"] = target
        return attrs


class SubmissionResponseSerializer(serializers.ModelSerializer):
    """Stable response shape for upload/status calls."""

    analysis = serializers.SerializerMethodField()

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
            "analysis",
        )
        read_only_fields = fields

    def get_analysis(self, obj: ContractSubmission):
        if obj.analysis_id is None:
            return None
        a = obj.analysis
        return {
            "public_short_id": a.public_short_id,
            "delivery_status": a.delivery_status,
            "link_expires_at": a.link_expires_at.isoformat() if a.link_expires_at else None,
        }
