"""HTTP: guarded resend — CS-248."""

from __future__ import annotations

import logging

from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from delivery.application.resend import ResendError, enqueue_resend

logger = logging.getLogger(__name__)


class ResendDeliveryView(APIView):
    """``POST /api/v1/contracts/<public_short_id>/resend/``"""

    authentication_classes = ()
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)

    def post(self, request, public_short_id: str):
        body = request.data if isinstance(request.data, dict) else {}
        target = body.get("target")
        if not target or not isinstance(target, str):
            return Response({"error": {"code": "INVALID_REQUEST"}}, status=400)

        logger.info("resend_requested", extra={"public_short_id": public_short_id.strip()})

        try:
            channel = enqueue_resend(public_short_id=public_short_id, target_raw=target)
        except ResendError as exc:
            status_map = {
                "TARGET_MISMATCH": 403,
                "RESEND_LIMIT_EXCEEDED": 429,
                "LINK_EXPIRED": 410,
                "NOT_FOUND": 404,
            }
            return Response(
                {"error": {"code": exc.code, "message": "La operación no está permitida."}},
                status=status_map.get(exc.code, 400),
            )

        return Response({"status": "accepted", "channel": channel}, status=202)
