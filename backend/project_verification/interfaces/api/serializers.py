"""Request bodies for `/api/v1/project-verification/manual/` (mirrors frontend validation.ts)."""

from __future__ import annotations

from rest_framework import serializers

_MANUAL_VERIFICATION_MAX_LEN = 240

_MESSAGES = {
    "developer_blank": "Indicá el desarrollador o constructor.",
    "project_blank": "Indicá el nombre del proyecto.",
    "permit_blank": "Indicá número o referencia de permiso.",
    "address_blank": "Indicá una dirección aproximada.",
}


def _max_len_message() -> str:
    return f"Máximo {_MANUAL_VERIFICATION_MAX_LEN} caracteres."


class ManualVerificationStubSerializer(serializers.Serializer):
    """Validated project-verification submission (manual fallback + billboard follow-up)."""

    developer = serializers.CharField(
        max_length=_MANUAL_VERIFICATION_MAX_LEN,
        trim_whitespace=True,
        required=True,
        allow_blank=False,
        error_messages={
            "required": _MESSAGES["developer_blank"],
            "blank": _MESSAGES["developer_blank"],
            "max_length": _max_len_message(),
        },
    )
    project = serializers.CharField(
        max_length=_MANUAL_VERIFICATION_MAX_LEN,
        trim_whitespace=True,
        required=True,
        allow_blank=False,
        error_messages={
            "required": _MESSAGES["project_blank"],
            "blank": _MESSAGES["project_blank"],
            "max_length": _max_len_message(),
        },
    )
    permit = serializers.CharField(
        max_length=_MANUAL_VERIFICATION_MAX_LEN,
        trim_whitespace=True,
        required=True,
        allow_blank=False,
        error_messages={
            "required": _MESSAGES["permit_blank"],
            "blank": _MESSAGES["permit_blank"],
            "max_length": _max_len_message(),
        },
    )
    address = serializers.CharField(
        max_length=_MANUAL_VERIFICATION_MAX_LEN,
        trim_whitespace=True,
        required=True,
        allow_blank=False,
        error_messages={
            "required": _MESSAGES["address_blank"],
            "blank": _MESSAGES["address_blank"],
            "max_length": _max_len_message(),
        },
    )

    submission_source = serializers.ChoiceField(
        choices=["manual", "billboard_ocr"],
        default="manual",
        required=False,
        allow_blank=False,
    )

    ocr_quality = serializers.ChoiceField(
        choices=["high", "medium", "low", "unknown"],
        required=False,
        allow_null=True,
        allow_blank=True,
    )
