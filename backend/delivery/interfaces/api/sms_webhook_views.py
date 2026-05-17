"""Inbound SMS provider status callbacks — CS-242."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging

from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings
from django.utils import timezone

from delivery.domain.enums import DeliveryRequestStatus
from delivery.infrastructure.django.models import DeliveryRequest

logger = logging.getLogger(__name__)


class SmsDeliveryCallbackView(APIView):
    """``POST /api/v1/webhooks/sms/`` — HMAC body verification (provider-specific)."""

    authentication_classes = ()
    permission_classes = (AllowAny,)

    def post(self, request) -> Response:
        secret = (getattr(settings, "SMS_WEBHOOK_SECRET", "") or "").strip()
        if not secret:
            logger.error("sms_webhook misconfigured: SMS_WEBHOOK_SECRET empty")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)

        raw = request.body
        sig_hdr = (request.headers.get("X-Sms-Signature") or "").strip()
        expected = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not sig_hdr or not hmac.compare_digest(expected, sig_hdr):
            return Response(status=status.HTTP_401_UNAUTHORIZED)

        try:
            payload = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            payload = {}

        if not isinstance(payload, dict):
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

        event = str(payload.get("event") or payload.get("type") or "").lower()
        msg_id = str(payload.get("provider_message_id") or payload.get("message_id") or "").strip()
        if not msg_id:
            logger.info("sms_webhook_no_message_id", extra={"event": event or "unknown"})
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

        _apply_sms_event(message_id=msg_id, event=event)
        logger.info(
            "sms_webhook_processed",
            extra={"event": event or "unknown", "provider_message_id": msg_id},
        )
        return Response({"status": "received"}, status=status.HTTP_200_OK)


def _apply_sms_event(*, message_id: str, event: str) -> None:
    row = DeliveryRequest.objects.filter(provider_message_id=message_id).first()
    if row is None:
        logger.info("sms_webhook_orphan", extra={"provider_message_id": message_id})
        return

    if "fail" in event:
        if row.status == DeliveryRequestStatus.DELIVERED.value:
            return
        row.status = DeliveryRequestStatus.FAILED.value
        row.last_error = "sms_provider_failed"
        row.save(update_fields=["status", "last_error"])
        return

    if "deliver" in event or "sent" in event:
        if row.status == DeliveryRequestStatus.DELIVERED.value:
            return

        row.status = DeliveryRequestStatus.DELIVERED.value
        row.delivered_at = timezone.now()
        row.save(update_fields=["status", "delivered_at"])
