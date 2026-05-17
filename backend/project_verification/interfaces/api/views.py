"""DRF endpoints for gated project-verification (EPIC-12)."""

from __future__ import annotations

from typing import Any

import structlog
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from project_verification.application.billboard_vision import extract_billboard_structured
from project_verification.application.evaluation import build_verdict_envelope
from shared.domain.exceptions import ForbiddenDomainException, ValidationDomainException

from .serializers import ManualVerificationRequestSerializer

logger = structlog.get_logger(__name__)


def _manual_detail() -> str:
    return "Datos procesados sin persistencia de imágenes; verificación opcional."


_VERDICT_DEMOS: dict[str, dict[str, Any]] = {
    "green": {
        "verdict": "green",
        "headline_key": "pv.headline.green.demo",
        "rationale_keys": [
            "permit.format_ok.year_serial.demo",
            "pv.reputation.skipped_disabled",
        ],
        "heuristic_score": 8.4,
        "data_freshness_note_key": "pv.freshness.demo",
    },
    "yellow": {
        "verdict": "yellow",
        "headline_key": "pv.headline.yellow.demo",
        "rationale_keys": [
            "pv.permit.format_unknown.free_text",
            "pv.reputation.skipped_disabled",
        ],
        "heuristic_score": 6.5,
        "data_freshness_note_key": "pv.freshness.demo",
    },
    "red": {
        "verdict": "red",
        "headline_key": "pv.headline.red.demo",
        "rationale_keys": [
            "permit.format_suspicious.generic",
            "pv.reputation.evidence_negative",
        ],
        "heuristic_score": 4.1,
        "data_freshness_note_key": "pv.freshness.demo",
    },
}


def _require_pv_enabled() -> None:

    if not getattr(settings, "PROJECT_VERIFICATION_ENABLED", False):

        raise ForbiddenDomainException(
            "Project verification is disabled for this deployment.",
            code="project_verification_disabled",
        )


class ProjectVerificationManualView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:

        _require_pv_enabled()

        serializer = ManualVerificationRequestSerializer(data=request.data)

        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        src_any = data.get("submission_source") or "manual"

        submission_source = "billboard_ocr" if src_any == "billboard_ocr" else "manual"

        envelope = build_verdict_envelope(
            developer=data["developer"],
            project=data["project"],
            permit=data["permit"],
            address=data["address"],
            submission_source=submission_source,
            ocr_quality=data.get("ocr_quality"),
        )

        envelope["detail"] = _manual_detail()

        logger.info(
            "project_verification.manual_evaluated",
            verdict=str(envelope.get("verdict")),
            submission_source=str(submission_source),
        )

        return Response(envelope, status=201)


class ProjectVerificationBillboardUploadView(APIView):
    permission_classes = (AllowAny,)

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request: Request) -> Response:

        _require_pv_enabled()

        upload = request.FILES.get("image")

        if upload is None:
            raise ValidationDomainException(
                "Falta el archivo image.",
                code="validation_error",
                status=400,
                details={"image": ["Imagen requerida."]},
            )

        ct = getattr(upload, "content_type", "") or "application/octet-stream"
        base_mime = ct.lower().split(";")[0].strip()
        allowed_ct = frozenset({"image/jpeg", "image/jpg", "image/png", "image/webp"})
        if base_mime not in allowed_ct:
            raise ValidationDomainException(
                "Tipo MIME no soportado para vallas.",
                code="unsupported_media",
                status=415,
                details={"image": ["Usá JPEG, PNG o WEBP."]},
            )

        blob = upload.read(settings.OCR_MAX_BYTES + 1)

        approx_bytes = len(blob)

        if approx_bytes > int(getattr(settings, "OCR_MAX_BYTES", 15 * 1024 * 1024)):

            raise ValidationDomainException(
                "Imagen demasiado grande.",
                code="billboard_payload_too_large",
                status=413,
                details={"image": ["Reduce el tamaño de la foto."]},
            )

        outcome = extract_billboard_structured(raw=blob, content_type=ct)

        ob = outcome.model_dump(mode="python")

        oq = "medium" if outcome.ocr_medium_confidence else ("high" if outcome.ocr_high_confidence else "low")

        fields = outcome.fields

        pref = {k: getattr(fields, k, None) for k in ("developer", "project", "permit", "address")}

        logger.info(
            "project_verification.billboard_evaluated",
            ocr_status=str(ob.get("ocr_status")),
            approximate_bytes=int(approx_bytes),
        )

        return Response(
            {
                **ob,
                "ocr_quality_hint": oq,
                "manual_prefill": pref,
                "detail": _manual_detail(),
            },
            status=200,
        )


_VERDICTS = frozenset(_VERDICT_DEMOS)


class ProjectVerificationDemoResultView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:

        _require_pv_enabled()

        raw = request.query_params.get("v") or "yellow"

        verdict_key = raw.strip().lower()

        if verdict_key not in _VERDICTS:

            verdict_key = "yellow"

        payload = dict(_VERDICT_DEMOS[verdict_key])

        payload["stub"] = True

        payload["detail"] = "Respuesta demo; usar POST /manual/ para veredictos reales."

        return Response(payload)
