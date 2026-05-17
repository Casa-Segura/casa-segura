"""Provider webhooks for delivery-related integrations."""

from __future__ import annotations

import json
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from delivery.interfaces.api.zavu_signature import verify_zavu_signature

logger = logging.getLogger(__name__)


class ZavuWebhookView(APIView):
    """`POST /api/v1/webhooks/zavu/` — acknowledge Zavu delivery / inbound events (MVP).

    Verifies ``X-Zavu-Signature`` per Zavu docs; does not persist payload contents.
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)
    parser_classes = ()

    def post(self, request) -> Response:
        secret = getattr(settings, "ZAVU_WEBHOOK_SECRET", "") or ""
        if not secret.strip():
            logger.error("zavu_webhook misconfigured: ZAVU_WEBHOOK_SECRET is empty")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        raw_body = request.body
        hdr = request.headers.get("X-Zavu-Signature")
        if not verify_zavu_signature(
            signature_header=hdr,
            raw_body=raw_body,
            secret=secret,
        ):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        event_type = None
        if raw_body:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
                if isinstance(payload, dict):
                    raw_type = payload.get("type")
                    if isinstance(raw_type, str):
                        event_type = raw_type
            except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
                pass

        if event_type:
            logger.info("zavu_webhook event_type=%s bytes=%s", event_type, len(raw_body))
        else:
            logger.info("zavu_webhook received bytes=%s", len(raw_body))

        return Response({"status": "received"}, status=status.HTTP_200_OK)
