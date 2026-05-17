"""DRF stubs for gated project-verification endpoints (EPIC-12 / CS-356)."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from shared.domain.exceptions import ForbiddenDomainException

from .serializers import ManualVerificationStubSerializer

logger = structlog.get_logger(__name__)


def _manual_detail() -> str:
    """Non-PII status line for stubs — keep short."""
    return "Recibimos los datos para referencia; stub sin persistencia (EPIC-12)"


_BILLBOARD_ACCEPT_DETAIL = "Imagen descartada en el stub sin persistencia. OCR real se enlaza en CS-350."


# Mirrors `frontend/src/lib/project-verification-fixtures.ts` verdict JSON shape.
_VERDICT_DEMOS: dict[str, dict[str, Any]] = {
    "green": {
        "verdict": "green",
        "headline": "Coincidencias alentadoras",
        "rationale": [
            "El expediente declarado aparece en el catálogo de ejemplo con estado vigente.",
            "No encontramos inconsistencias obvias entre el nombre del proyecto y el desarrollador.",
        ],
        "data_freshness_note": "Datos de reputación simulados al 15 may 2026 (stub).",
    },
    "yellow": {
        "verdict": "yellow",
        "headline": "Revisá con calma",
        "rationale": [
            "Hay coincidencia parcial: el permiso podría corresponder a una fase distinta.",
            "Te recomendamos confirmar en la municipalidad antes de tomar una decisión.",
        ],
        "data_freshness_note": "Datos de reputación simulados al 15 may 2026 (stub).",
    },
    "red": {
        "verdict": "red",
        "headline": "Riesgos detectados (demo)",
        "rationale": [
            "No encontramos el permiso en el conjunto de prueba o el formato no coincide.",
            "Esto no bloquea el análisis de tu contrato en /subir.",
        ],
        "data_freshness_note": "Datos de reputación simulados al 15 may 2026 (stub).",
    },
}


def _require_pv_enabled() -> None:
    if not getattr(settings, "PROJECT_VERIFICATION_ENABLED", False):
        raise ForbiddenDomainException(
            "Project verification is disabled for this deployment.",
            code="project_verification_disabled",
        )


class ProjectVerificationManualStubView(APIView):
    permission_classes = (AllowAny,)

    def post(self, request: Request) -> Response:
        _require_pv_enabled()
        serializer = ManualVerificationStubSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        echo = {
            "developer": data["developer"],
            "project": data["project"],
            "permit": data["permit"],
            "address": data["address"],
        }
        ref = str(uuid.uuid4())
        logger.info(
            "project_verification.manual_stub.created",
            stub=True,
        )
        return Response(
            {
                "reference_id": ref,
                "echo": echo,
                "detail": _manual_detail(),
                "stub": True,
            },
            status=201,
        )


class ProjectVerificationBillboardUploadStubView(APIView):
    permission_classes = (AllowAny,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request: Request) -> Response:
        _require_pv_enabled()
        # Discard body contents; optionally record non-PII size for counters.
        image = request.FILES.get("image")
        approx_bytes = int(getattr(image, "size", 0) or 0)
        logger.info(
            "project_verification.billboard_stub.accepted",
            stub=True,
            approximate_bytes=approx_bytes,
        )
        payload: dict[str, Any] = {
            "detail": _BILLBOARD_ACCEPT_DETAIL,
            "stub": True,
        }
        return Response(payload, status=202)


_VERDICTS = frozenset(_VERDICT_DEMOS)


class ProjectVerificationDemoResultStubView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        _require_pv_enabled()
        raw = request.query_params.get("v") or "yellow"
        verdict_key = raw.strip().lower()
        if verdict_key not in _VERDICTS:
            verdict_key = "yellow"
        return Response(_VERDICT_DEMOS[verdict_key])
